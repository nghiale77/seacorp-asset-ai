"""Sinh mã hồ sơ yêu cầu ASR-YYYYMM-XXXXX (mục Bước 1 của tài liệu nghiệp vụ)."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.timeutils import utcnow
from app.models.request import AssetRequest


def generate_request_id(db: Session, as_of: dt.datetime | None = None) -> str:
    as_of = as_of or utcnow()
    prefix = f"ASR-{as_of:%Y%m}-"

    count = (
        db.query(func.count(AssetRequest.request_id))
        .filter(AssetRequest.request_id.like(f"{prefix}%"))
        .scalar()
    ) or 0

    seq = count + 1
    return f"{prefix}{seq:05d}"
