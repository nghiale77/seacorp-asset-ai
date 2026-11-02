"""Kiểm thử manual_intake — Bước 1 tiếp nhận yêu cầu, sinh mã ASR-YYYYMM-XXXXX,
gắn cờ nghi trùng (kịch bản 6) nhưng KHÔNG tự động gộp hồ sơ."""
from __future__ import annotations

import datetime as dt

import pytest

from app.integrations.manual_intake import submit_request
from app.models.request import AssetRequest, RequestDocument


def test_submit_request_generates_id_and_persists(db_session):
    req = submit_request(
        db_session, sender_name="Lê Văn Kho Vận", sender_email="req_danny01@seacorp.local",
        company_code="DANNYGREEN", original_content="Cần 1 xe tải 5 tấn.",
        received_at=dt.datetime(2026, 11, 1),
    )
    assert req.request_id.startswith("ASR-202611-")
    assert req.status == "NEW"
    assert db_session.get(AssetRequest, req.request_id) is not None


def test_sequential_requests_get_incrementing_numbers(db_session):
    req1 = submit_request(db_session, sender_name="A", original_content="Nội dung 1",
                           received_at=dt.datetime(2026, 11, 1))
    req2 = submit_request(db_session, sender_name="B", original_content="Nội dung khác hẳn 2",
                           received_at=dt.datetime(2026, 11, 2))
    assert req1.request_id != req2.request_id
    assert req1.request_id.endswith("00001")
    assert req2.request_id.endswith("00002")


def test_scenario6_duplicate_is_flagged_but_still_creates_separate_record(db_session):
    content = "Đề nghị cấp 1 xe tải cảng 5 tấn phục vụ kho Bình Dương, cần trong tháng tới."
    req1 = submit_request(db_session, sender_name="Lê Văn Kho Vận", sender_email="req_danny01@seacorp.local",
                           original_content=content, received_at=dt.datetime(2026, 11, 1))
    req2 = submit_request(db_session, sender_name="Lê Văn Kho Vận", sender_email="req_danny01@seacorp.local",
                           original_content=content + " (nhắc lại)", received_at=dt.datetime(2026, 11, 3))

    assert req2.suspected_duplicate is True
    assert req2.duplicate_of_request_id == req1.request_id
    # Không tự động gộp — hồ sơ 2 vẫn tồn tại độc lập để QLTS&ĐT xác nhận.
    assert db_session.get(AssetRequest, req2.request_id) is not None


def test_attachments_are_persisted(db_session):
    req = submit_request(
        db_session, sender_name="A", original_content="Có đính kèm ảnh.",
        attachments=[{"file_name": "bao_gia.pdf", "file_link": "file://bao_gia.pdf"}],
    )
    docs = db_session.query(RequestDocument).filter_by(request_id=req.request_id).all()
    assert len(docs) == 1
    assert docs[0].file_name == "bao_gia.pdf"


def test_missing_content_raises():
    import app.database.session as _  # noqa: F401  (đảm bảo import không lỗi)

    with pytest.raises(ValueError):
        submit_request(None, sender_name="A", original_content="   ")
