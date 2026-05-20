from __future__ import annotations

import base64
import hashlib
import hmac
import json
from typing import Any

DEV_KEY = b"delegate-scope-local-dev-signing-key"


def canonical(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sign(payload: dict[str, Any]) -> str:
    digest = hmac.new(DEV_KEY, canonical(payload), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def verify_signature(payload: dict[str, Any], signature: str) -> bool:
    return hmac.compare_digest(sign(payload), signature)


def did_subject(inquiry_id: str) -> str:
    digest = hashlib.sha256(inquiry_id.encode("utf-8")).hexdigest()[:24]
    return f"did:subject:{digest}"


def agent_did(name: str, inquiry_id: str) -> str:
    digest = hashlib.sha256(f"{name}:{inquiry_id}".encode("utf-8")).hexdigest()[:24]
    return f"did:key:z{digest}"
