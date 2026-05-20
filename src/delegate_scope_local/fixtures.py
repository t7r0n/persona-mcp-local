from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from delegate_scope_local.models import Inquiry, project_root


class InquiryFile(BaseModel):
    inquiries: list[Inquiry]


def fixture_path() -> Path:
    return project_root() / "fixtures" / "inquiries.json"


def load_inquiries(path: Path | None = None) -> dict[str, Inquiry]:
    target = path or fixture_path()
    with target.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    parsed = InquiryFile.model_validate(payload)
    return {inquiry.inquiry_id: inquiry for inquiry in parsed.inquiries}
