"""Kiểm thử ai_analysis_service — kịch bản (5) thiếu thông tin, (6) trùng lặp,
và nguyên tắc không suy diễn khi chưa cấu hình AI."""
from __future__ import annotations

import datetime as dt
from types import SimpleNamespace

import app.services.ai_analysis_service as ai_service
from app.services.ai_analysis_service import NOT_ENOUGH_BASIS, ExtractedFields, run_ai_analysis

from tests.conftest import make_request


class FakeSettings:
    def __init__(self, ai_enabled: bool):
        self.ai_enabled = ai_enabled
        self.ai_model = "claude-sonnet-5"
        self.anthropic_api_key = "fake-key" if ai_enabled else ""


def test_scenario5_missing_info_falls_back_without_api_key(db_session, monkeypatch):
    monkeypatch.setattr(ai_service, "get_settings", lambda: FakeSettings(ai_enabled=False))
    make_request(
        db_session, sender_email="req_farm01@seacorp.local",
        original_content="Farm cần thêm thiết bị để làm việc, mong Phòng hỗ trợ sớm.",
    )

    req = run_ai_analysis(db_session, "ASR-202611-00001")

    assert req.ai_completeness == "Thiếu thông tin"
    assert NOT_ENOUGH_BASIS in req.ai_confidence_note
    assert req.proposed_asset_info == "Farm cần thêm thiết bị để làm việc, mong Phòng hỗ trợ sớm."


def test_scenario6_duplicate_short_circuits_ai_call(db_session, monkeypatch):
    called = {"n": 0}

    def _fail_if_called(*args, **kwargs):
        called["n"] += 1
        raise AssertionError("Không nên gọi Claude API khi đã phát hiện trùng lặp")

    monkeypatch.setattr(ai_service, "get_settings", lambda: FakeSettings(ai_enabled=True))
    monkeypatch.setattr(ai_service, "_extract_via_claude", _fail_if_called)

    content = "Đề nghị cấp 1 xe tải cảng 5 tấn phục vụ kho Bình Dương, cần trong tháng tới."
    make_request(
        db_session, request_id="ASR-202611-00001", sender_email="req_danny01@seacorp.local",
        original_content=content, received_at=dt.datetime(2026, 11, 1),
    )
    make_request(
        db_session, request_id="ASR-202611-00002", sender_email="req_danny01@seacorp.local",
        original_content=content + " (nhắc lại)", received_at=dt.datetime(2026, 11, 3),
    )

    req = run_ai_analysis(db_session, "ASR-202611-00002")

    assert req.ai_completeness == "Trùng yêu cầu"
    assert req.suspected_duplicate is True
    assert req.duplicate_of_request_id == "ASR-202611-00001"
    assert called["n"] == 0


def test_successful_extraction_populates_structured_fields(db_session, monkeypatch):
    fake_extraction = ExtractedFields(
        unit_info="DannyGreen Logistics, kho Bình Dương, Lê Văn Kho Vận",
        asset_info="Xe tải 5 tấn",
        usage_need="Trung chuyển hàng hóa nội bộ",
        efficiency_info=NOT_ENOUGH_BASIS,
        completeness="Đầy đủ",
        confidence_note="Đủ thông tin đơn vị, tài sản, mục đích và số lượng.",
        asset_group="Xe tải", requested_quantity=1, requested_capacity=5,
        requested_location_province="Bình Dương", needed_by_date="2026-12-01",
    )
    monkeypatch.setattr(ai_service, "get_settings", lambda: FakeSettings(ai_enabled=True))
    monkeypatch.setattr(ai_service, "_extract_via_claude", lambda content: fake_extraction)

    make_request(db_session, asset_group=None, requested_quantity=None, requested_capacity=None,
                 requested_location_province=None, needed_by_date=None)

    req = run_ai_analysis(db_session, "ASR-202611-00001")

    assert req.ai_completeness == "Đầy đủ"
    assert req.asset_group == "Xe tải"
    assert float(req.requested_quantity) == 1
    assert float(req.requested_capacity) == 5
    assert req.requested_location_province == "Bình Dương"
    assert req.needed_by_date == dt.date(2026, 12, 1)


def test_claude_api_error_falls_back_gracefully(db_session, monkeypatch):
    def _boom(content):
        raise RuntimeError("network down")

    monkeypatch.setattr(ai_service, "get_settings", lambda: FakeSettings(ai_enabled=True))
    monkeypatch.setattr(ai_service, "_extract_via_claude", _boom)

    make_request(db_session, original_content="Nội dung bất kỳ.")
    req = run_ai_analysis(db_session, "ASR-202611-00001")

    assert req.ai_completeness == "Thiếu thông tin"
    assert "Lỗi gọi Claude API" in req.ai_confidence_note
