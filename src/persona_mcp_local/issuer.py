from __future__ import annotations

import time
import uuid

from persona_mcp_local.crypto import agent_did, did_persona, sign, verify_signature
from persona_mcp_local.fixtures import load_inquiries
from persona_mcp_local.models import AgentCredential, InquiryStatus, Presentation, VerificationResult

REGISTRY: dict[str, AgentCredential] = {}
REVOKED: set[str] = set()


def reset_state() -> None:
    REGISTRY.clear()
    REVOKED.clear()


def credential_payload(credential: AgentCredential) -> dict[str, object]:
    payload = credential.model_dump()
    payload.pop("signature", None)
    return payload


def presentation_payload(presentation: Presentation) -> dict[str, object]:
    payload = presentation.model_dump()
    payload.pop("signature", None)
    return payload


def register_agent(inquiry_id: str, scopes: list[str], ttl_minutes: int, agent_name: str = "local-agent") -> AgentCredential:
    inquiries = load_inquiries()
    inquiry = inquiries[inquiry_id]
    if inquiry.status != InquiryStatus.VERIFIED:
        raise ValueError(inquiry.failure_reason or "Inquiry is not verified.")
    if inquiry.liveness_score < 0.9 or inquiry.deepfake_score > 0.15:
        raise ValueError("verification failed: liveness anomaly")
    now = int(time.time())
    credential = AgentCredential(
        credential_id=f"vc_{uuid.uuid4().hex[:12]}",
        holder=did_persona(inquiry.inquiry_id),
        subject=agent_did(agent_name, inquiry.inquiry_id),
        inquiry_id=inquiry.inquiry_id,
        scopes=scopes,
        issued_at=now,
        expires_at=now + ttl_minutes * 60,
        signature="",
    )
    credential.signature = sign(credential_payload(credential))
    REGISTRY[credential.credential_id] = credential
    return credential


def present(credential_id: str, audience: str, scopes: list[str] | None = None, ttl_minutes: int = 5) -> Presentation:
    credential = REGISTRY[credential_id]
    requested = scopes or credential.scopes
    missing = sorted(set(requested) - set(credential.scopes))
    if missing:
        raise ValueError(f"scope escalation requires fresh inquiry: {','.join(missing)}")
    if credential.credential_id in REVOKED:
        raise ValueError("credential revoked")
    now = int(time.time())
    presentation = Presentation(
        presentation_id=f"vp_{uuid.uuid4().hex[:12]}",
        credential_id=credential.credential_id,
        subject=credential.subject,
        audience=audience,
        scopes=requested,
        issued_at=now,
        expires_at=min(now + ttl_minutes * 60, credential.expires_at),
        signature="",
    )
    presentation.signature = sign(presentation_payload(presentation))
    return presentation


def verify_presentation(presentation: Presentation, audience: str, required_scope: str | None = None) -> VerificationResult:
    started = time.perf_counter()
    credential = REGISTRY.get(presentation.credential_id)
    reason = "valid"
    valid = True
    if not credential:
        valid, reason = False, "unknown credential"
    elif credential.credential_id in REVOKED:
        valid, reason = False, "credential revoked"
    elif int(time.time()) > presentation.expires_at:
        valid, reason = False, "presentation expired"
    elif presentation.audience != audience:
        valid, reason = False, "audience mismatch"
    elif required_scope and required_scope not in presentation.scopes:
        valid, reason = False, "required scope missing"
    elif not verify_signature(presentation_payload(presentation), presentation.signature):
        valid, reason = False, "invalid presentation signature"
    elif not verify_signature(credential_payload(credential), credential.signature):
        valid, reason = False, "invalid credential signature"
    return VerificationResult(
        valid=valid,
        reason=reason,
        subject=presentation.subject if valid else None,
        holder=credential.holder if credential and valid else None,
        scopes=presentation.scopes if valid else [],
        latency_ms=round((time.perf_counter() - started) * 1000, 4),
    )


def revoke(credential_id: str) -> None:
    REVOKED.add(credential_id)
