from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from delegate_scope_local.dashboard import build_dashboard
from delegate_scope_local.issuer import present, register_agent, reset_state, revoke, verify_presentation
from delegate_scope_local.runner import init_demo, run_suite, verify_outputs


def test_register_present_verify_revoke_flow() -> None:
    reset_state()
    credential = register_agent("inq_verified_001", ["payments:read"], 30)
    presentation = present(credential.credential_id, "mock-bank", ["payments:read"], 5)
    assert verify_presentation(presentation, "mock-bank", "payments:read").valid is True
    revoke(credential.credential_id)
    revoked = verify_presentation(presentation, "mock-bank", "payments:read")
    assert revoked.valid is False
    assert revoked.reason == "credential revoked"


def test_deepfake_inquiry_is_structured_rejection() -> None:
    reset_state()
    with pytest.raises(ValueError, match="liveness anomaly"):
        register_agent("inq_deepfake_001", ["payments:read"], 30)


def test_scope_escalation_requires_fresh_inquiry() -> None:
    reset_state()
    credential = register_agent("inq_verified_001", ["payments:read"], 30)
    with pytest.raises(ValueError, match="scope escalation"):
        present(credential.credential_id, "mock-bank", ["payments:write"], 5)


def test_end_to_end_suite_verify_dashboard() -> None:
    init_demo(force=True)
    summary = run_suite(iterations=100)
    report = verify_outputs()
    assert summary.verify_p95_latency_ms < 25
    assert summary.failed_liveness_rejections >= 100
    assert report["passed"] is True
    html = Path(build_dashboard()).read_text(encoding="utf-8")
    assert "Agent Identity Delegation Dashboard" in html
    assert "Verification passed" in html


def test_stdio_register_rejection_contract() -> None:
    process = subprocess.run(
        [sys.executable, "-m", "delegate_scope_local.cli", "stdio"],
        input='{"tool":"agent.register","inquiry_id":"inq_deepfake_001","scopes":["payments:read"],"ttl_minutes":30}\n',
        text=True,
        capture_output=True,
        check=True,
    )
    response = json.loads(process.stdout)
    assert response["ok"] is False
    assert "liveness anomaly" in response["reason"]
