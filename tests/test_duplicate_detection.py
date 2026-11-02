"""Kịch bản 6 — yêu cầu trùng lặp: người gửi bổ sung nội dung cho hồ sơ đang
xử lý không được tạo thành hồ sơ mới tách biệt mà phải được gợi ý liên kết."""
from __future__ import annotations

import datetime as dt

from app.services.duplicate_detection import find_possible_duplicate

from tests.conftest import make_request


def test_near_identical_content_same_sender_is_duplicate(db_session):
    content = "Đề nghị cấp 1 xe tải cảng 5 tấn phục vụ kho Bình Dương, cần trong tháng tới."
    make_request(
        db_session, request_id="ASR-202611-00001",
        sender_email="req_danny01@seacorp.local", original_content=content,
        received_at=dt.datetime(2026, 11, 1),
    )

    duplicate = find_possible_duplicate(
        db_session, sender_email="req_danny01@seacorp.local",
        original_content=content + " (nhắc lại vì chưa thấy phản hồi)",
        received_at=dt.datetime(2026, 11, 3),
    )
    assert duplicate is not None
    assert duplicate.request_id == "ASR-202611-00001"


def test_different_sender_not_flagged(db_session):
    content = "Đề nghị cấp 1 xe tải cảng 5 tấn phục vụ kho Bình Dương, cần trong tháng tới."
    make_request(
        db_session, request_id="ASR-202611-00001",
        sender_email="req_danny01@seacorp.local", original_content=content,
        received_at=dt.datetime(2026, 11, 1),
    )

    duplicate = find_possible_duplicate(
        db_session, sender_email="req_farm01@seacorp.local",
        original_content=content, received_at=dt.datetime(2026, 11, 3),
    )
    assert duplicate is None


def test_closed_request_excluded_from_duplicate_check(db_session):
    content = "Đề nghị cấp 1 xe tải cảng 5 tấn phục vụ kho Bình Dương, cần trong tháng tới."
    make_request(
        db_session, request_id="ASR-202611-00001",
        sender_email="req_danny01@seacorp.local", original_content=content,
        received_at=dt.datetime(2026, 11, 1), status="CLOSED",
    )

    duplicate = find_possible_duplicate(
        db_session, sender_email="req_danny01@seacorp.local",
        original_content=content, received_at=dt.datetime(2026, 11, 3),
    )
    assert duplicate is None


def test_outside_lookback_window_not_flagged(db_session):
    content = "Đề nghị cấp 1 xe tải cảng 5 tấn phục vụ kho Bình Dương, cần trong tháng tới."
    make_request(
        db_session, request_id="ASR-202611-00001",
        sender_email="req_danny01@seacorp.local", original_content=content,
        received_at=dt.datetime(2026, 1, 1),
    )

    duplicate = find_possible_duplicate(
        db_session, sender_email="req_danny01@seacorp.local",
        original_content=content, received_at=dt.datetime(2026, 11, 3),
    )
    assert duplicate is None
