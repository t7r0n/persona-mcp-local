from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field


class InquiryStatus(StrEnum):
    VERIFIED = "verified"
    FAILED = "failed"
    PENDING = "pending"


class EventKind(StrEnum):
    REGISTER = "register"
    PRESENT = "present"
    VERIFY = "verify"
    REVOKE = "revoke"


class Inquiry(BaseModel):
    inquiry_id: str
    human_subject: str
    status: InquiryStatus
    liveness_score: float
    deepfake_score: float
    assurance_level: str
    failure_reason: str | None = None


class AgentCredential(BaseModel):
    credential_id: str
    issuer: str = "did:web:local-persona.example"
    holder: str
    subject: str
    inquiry_id: str
    scopes: list[str]
    issued_at: int
    expires_at: int
    signature: str


class Presentation(BaseModel):
    presentation_id: str
    credential_id: str
    subject: str
    audience: str
    scopes: list[str]
    issued_at: int
    expires_at: int
    signature: str


class VerificationResult(BaseModel):
    valid: bool
    reason: str
    subject: str | None = None
    holder: str | None = None
    scopes: list[str] = Field(default_factory=list)
    latency_ms: float


class Event(BaseModel):
    run_id: str
    kind: EventKind
    ok: bool
    reason: str
    latency_ms: float
    credential_id: str | None = None
    inquiry_id: str | None = None


class RunSummary(BaseModel):
    run_id: str
    event_count: int
    successful_registrations: int
    failed_liveness_rejections: int
    scope_escalations_rejected: int
    revocation_checks_passed: int
    verify_p95_latency_ms: float
    verify_throughput_per_second: float
    pass_gates: bool


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]
