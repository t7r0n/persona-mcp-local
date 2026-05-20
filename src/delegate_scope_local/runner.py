from __future__ import annotations

import shutil
import statistics
import time
import uuid
from pathlib import Path
from typing import Any

import duckdb

from delegate_scope_local.issuer import present, register_agent, reset_state, revoke, verify_presentation
from delegate_scope_local.models import Event, EventKind, RunSummary, project_root


def init_demo(force: bool = False) -> dict[str, str]:
    root = project_root()
    for name in ("data", "runs", "outputs"):
        path = root / name
        if force and path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True, exist_ok=True)
    return {"fixtures": str(root / "fixtures" / "inquiries.json"), "outputs": str(root / "outputs")}


def connect_store(path: Path) -> duckdb.DuckDBPyConnection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(path))
    conn.execute(
        """
        create table if not exists events (
          run_id varchar,
          kind varchar,
          ok boolean,
          reason varchar,
          latency_ms double,
          credential_id varchar,
          inquiry_id varchar
        )
        """
    )
    return conn


def persist(conn: duckdb.DuckDBPyConnection, event: Event) -> None:
    conn.execute(
        "insert into events values (?, ?, ?, ?, ?, ?, ?)",
        [
            event.run_id,
            event.kind.value,
            event.ok,
            event.reason,
            event.latency_ms,
            event.credential_id,
            event.inquiry_id,
        ],
    )


def timed_event(run_id: str, kind: EventKind, fn, credential_id: str | None = None, inquiry_id: str | None = None) -> tuple[Event, Any]:
    started = time.perf_counter()
    try:
        result = fn()
        return (
            Event(
                run_id=run_id,
                kind=kind,
                ok=True,
                reason="ok",
                latency_ms=round((time.perf_counter() - started) * 1000, 4),
                credential_id=credential_id or getattr(result, "credential_id", None),
                inquiry_id=inquiry_id,
            ),
            result,
        )
    except Exception as exc:
        return (
            Event(
                run_id=run_id,
                kind=kind,
                ok=False,
                reason=str(exc),
                latency_ms=round((time.perf_counter() - started) * 1000, 4),
                credential_id=credential_id,
                inquiry_id=inquiry_id,
            ),
            None,
        )


def p95(values: list[float]) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    return statistics.quantiles(values, n=100, method="inclusive")[94]


def run_suite(iterations: int = 100) -> RunSummary:
    init_demo()
    reset_state()
    run_id = f"run-{uuid.uuid4().hex[:12]}"
    root = project_root()
    run_dir = root / "runs" / "latest"
    if run_dir.exists():
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    conn = connect_store(run_dir / "identity.duckdb")
    stream_path = root / "outputs" / "event_stream.jsonl"
    if stream_path.exists():
        stream_path.unlink()
    events: list[Event] = []
    verifies: list[float] = []
    with stream_path.open("w", encoding="utf-8") as stream:
        for _ in range(iterations):
            event, credential = timed_event(
                run_id,
                EventKind.REGISTER,
                lambda: register_agent("inq_verified_001", ["payments:read"], 30),
                inquiry_id="inq_verified_001",
            )
            events.append(event)
            if credential:
                event2, presentation = timed_event(
                    run_id,
                    EventKind.PRESENT,
                    lambda: present(credential.credential_id, "mock-bank", ["payments:read"], 5),
                    credential_id=credential.credential_id,
                )
                events.append(event2)
                if presentation:
                    started = time.perf_counter()
                    result = verify_presentation(presentation, "mock-bank", "payments:read")
                    latency = (time.perf_counter() - started) * 1000
                    verifies.append(latency)
                    events.append(
                        Event(
                            run_id=run_id,
                            kind=EventKind.VERIFY,
                            ok=result.valid,
                            reason=result.reason,
                            latency_ms=result.latency_ms,
                            credential_id=credential.credential_id,
                            inquiry_id=credential.inquiry_id,
                        )
                    )
                    revoke(credential.credential_id)
                    revoked_result = verify_presentation(presentation, "mock-bank", "payments:read")
                    events.append(
                        Event(
                            run_id=run_id,
                            kind=EventKind.REVOKE,
                            ok=not revoked_result.valid and revoked_result.reason == "credential revoked",
                            reason=revoked_result.reason,
                            latency_ms=revoked_result.latency_ms,
                            credential_id=credential.credential_id,
                            inquiry_id=credential.inquiry_id,
                        )
                    )
            failed_event, _ = timed_event(
                run_id,
                EventKind.REGISTER,
                lambda: register_agent("inq_deepfake_001", ["payments:read"], 30),
                inquiry_id="inq_deepfake_001",
            )
            events.append(failed_event)
            scope_event, _ = timed_event(
                run_id,
                EventKind.PRESENT,
                lambda: present(credential.credential_id, "mock-bank", ["payments:write"], 5) if credential else None,
                credential_id=getattr(credential, "credential_id", None),
            )
            if credential:
                events.append(scope_event)
        for event in events:
            persist(conn, event)
            stream.write(event.model_dump_json() + "\n")
    conn.close()
    success = sum(1 for event in events if event.kind == EventKind.REGISTER and event.ok)
    failed_liveness = sum(1 for event in events if event.kind == EventKind.REGISTER and not event.ok)
    scope_reject = sum(1 for event in events if event.kind == EventKind.PRESENT and not event.ok and "scope escalation" in event.reason)
    revocation = sum(1 for event in events if event.kind == EventKind.REVOKE and event.ok)
    elapsed = sum(verifies) / 1000 if verifies else 0.001
    summary = RunSummary(
        run_id=run_id,
        event_count=len(events),
        successful_registrations=success,
        failed_liveness_rejections=failed_liveness,
        scope_escalations_rejected=scope_reject,
        revocation_checks_passed=revocation,
        verify_p95_latency_ms=round(p95(verifies), 4),
        verify_throughput_per_second=round(len(verifies) / max(elapsed, 0.001), 2),
        pass_gates=success >= iterations
        and failed_liveness >= iterations
        and scope_reject >= iterations
        and revocation >= iterations
        and p95(verifies) < 25,
    )
    (root / "outputs" / "summary.json").write_text(summary.model_dump_json(indent=2), encoding="utf-8")
    return summary


def verify_outputs() -> dict[str, Any]:
    root = project_root()
    summary_path = root / "outputs" / "summary.json"
    stream_path = root / "outputs" / "event_stream.jsonl"
    db_path = root / "runs" / "latest" / "identity.duckdb"
    if not summary_path.exists() or not stream_path.exists() or not db_path.exists():
        raise FileNotFoundError("Run `uv run delegate-scope-local run-suite` before verification.")
    summary = RunSummary.model_validate_json(summary_path.read_text(encoding="utf-8"))
    conn = duckdb.connect(str(db_path), read_only=True)
    event_count = conn.execute("select count(*) from events").fetchone()[0]
    bad_verify = conn.execute("select count(*) from events where kind = 'verify' and ok = false").fetchone()[0]
    conn.close()
    stream_count = sum(1 for _ in stream_path.open("r", encoding="utf-8"))
    checks = {
        "required_outputs_present": summary_path.exists() and stream_path.exists() and db_path.exists(),
        "event_count_matches_stream": event_count == stream_count == summary.event_count,
        "successful_registration_path": summary.successful_registrations >= 100,
        "deepfake_rejections_present": summary.failed_liveness_rejections >= 100,
        "scope_escalations_rejected": summary.scope_escalations_rejected >= 100,
        "revocation_enforced": summary.revocation_checks_passed >= 100,
        "valid_presentations_verify": bad_verify == 0,
        "verify_p95_under_25ms": summary.verify_p95_latency_ms < 25,
    }
    return {"run_id": summary.run_id, "summary": summary.model_dump(), "checks": checks, "passed": all(checks.values())}


def export_demo_pack() -> Path:
    root = project_root()
    pack = root / "outputs" / "demo_pack"
    if pack.exists():
        shutil.rmtree(pack)
    pack.mkdir(parents=True, exist_ok=True)
    for name in ("summary.json", "event_stream.jsonl", "dashboard.html"):
        source = root / "outputs" / name
        if source.exists():
            shutil.copy2(source, pack / name)
    shutil.copy2(root / "fixtures" / "inquiries.json", pack / "inquiries.json")
    return pack
