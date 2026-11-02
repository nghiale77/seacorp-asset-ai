"""Chống tạo hồ sơ trùng lặp khi người gửi trả lời/bổ sung cho yêu cầu đang xử lý
(mục Bước 1). Chỉ GỢI Ý nghi trùng — không tự động gộp hoặc đóng hồ sơ; người
dùng (Phòng QLTS&ĐT) xác nhận."""
from __future__ import annotations

import datetime as dt
import difflib

from sqlalchemy.orm import Session

from app.models.request import AssetRequest

DUPLICATE_LOOKBACK_DAYS = 30
CONTENT_SIMILARITY_THRESHOLD = 0.6
OPEN_STATUSES_EXCLUDED_FROM_DUPLICATE_CHECK = {"CLOSED", "REJECTED"}


def find_possible_duplicate(
    db: Session,
    sender_email: str | None,
    original_content: str,
    received_at: dt.datetime,
    exclude_request_id: str | None = None,
) -> AssetRequest | None:
    if not sender_email:
        return None

    window_start = received_at - dt.timedelta(days=DUPLICATE_LOOKBACK_DAYS)
    query = (
        db.query(AssetRequest)
        .filter(
            AssetRequest.sender_email == sender_email,
            AssetRequest.received_at >= window_start,
            AssetRequest.received_at <= received_at,
            ~AssetRequest.status.in_(OPEN_STATUSES_EXCLUDED_FROM_DUPLICATE_CHECK),
        )
    )
    if exclude_request_id:
        query = query.filter(AssetRequest.request_id != exclude_request_id)
    candidates = query.order_by(AssetRequest.received_at.desc()).all()

    for candidate in candidates:
        similarity = difflib.SequenceMatcher(
            None, candidate.original_content.lower(), original_content.lower()
        ).ratio()
        if similarity >= CONTENT_SIMILARITY_THRESHOLD:
            return candidate
    return None
