"""Kênh tiếp nhận mặc định của Giai đoạn 1 — Bước 1 (tiếp nhận yêu cầu).

Thay cho việc nối Outlook/Gmail/Teams thật (chưa có quyền truy cập trong môi
trường này), chuyên viên/đơn vị đề xuất nhập yêu cầu qua form nội bộ (Streamlit)
hoặc nạp nội dung email đã có sẵn (copy/paste) làm `original_content`. Toàn bộ
quy tắc nghiệp vụ Bước 1 (mã hồ sơ, chống trùng, lưu hồ sơ gốc) được áp dụng
giống như khi nhận qua email thật — khi Giai đoạn 2 nối Outlook/Gmail/Teams,
chỉ cần thay nguồn gọi submit_request(), không đổi logic nghiệp vụ.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy.orm import Session

from app.core.timeutils import utcnow
from app.integrations.base import IntakeProvider
from app.models.request import AssetRequest, RequestDocument
from app.services.duplicate_detection import find_possible_duplicate
from app.services.numbering import generate_request_id


class ManualIntakeProvider(IntakeProvider):
    def fetch_new_messages(self) -> list[dict]:
        raise NotImplementedError(
            "ManualIntakeProvider dùng mô hình submit trực tiếp (submit_request), không fetch định kỳ."
        )


def submit_request(
    db: Session,
    sender_name: str,
    original_content: str,
    sender_email: str | None = None,
    company_code: str | None = None,
    department_code: str | None = None,
    asset_group: str | None = None,
    channel: str = "manual_intake",
    attachments: list[dict] | None = None,
    received_at: dt.datetime | None = None,
) -> AssetRequest:
    """Tạo hồ sơ yêu cầu mới. Không tạo hồ sơ trùng lặp khi người gửi bổ sung
    cho yêu cầu đang xử lý — chỉ GẮN CỜ nghi trùng, vẫn tạo hồ sơ riêng để
    Phòng QLTS&ĐT xác nhận gộp/liên kết thủ công, không tự động gộp."""
    if not sender_name or not sender_name.strip():
        raise ValueError("Thiếu tên người gửi/đơn vị đề xuất.")
    if not original_content or not original_content.strip():
        raise ValueError("Thiếu nội dung yêu cầu.")

    now = received_at or utcnow()
    request_id = generate_request_id(db, now)

    duplicate = find_possible_duplicate(db, sender_email, original_content, now)

    request = AssetRequest(
        request_id=request_id, sender_name=sender_name, sender_email=sender_email,
        company_code=company_code, department_code=department_code,
        received_at=now, channel=channel, original_content=original_content,
        asset_group=asset_group,
        suspected_duplicate=duplicate is not None,
        duplicate_of_request_id=duplicate.request_id if duplicate else None,
        status="NEW", created_at=now,
    )
    db.add(request)
    db.flush()

    for doc in (attachments or []):
        db.add(RequestDocument(
            request_id=request_id, file_name=doc["file_name"], file_link=doc["file_link"],
            file_type=doc.get("file_type"), uploaded_by=doc.get("uploaded_by", sender_name),
            uploaded_at=now,
        ))

    db.flush()
    return request
