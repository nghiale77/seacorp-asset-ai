"""Kiểm thử asset_matching_service — bám các kịch bản tối thiểu trong tài liệu:
(1) đầy đủ + có tài sản nhàn rỗi phù hợp, (2) có tài sản nhưng công suất
không đủ, (3) có tài sản nhưng cần sửa chữa, (4) không có tài sản phù hợp.
"""
from __future__ import annotations

import datetime as dt

import pytest

from app.core.rbac import PermissionDenied, UserContext
from app.models.asset import AssetCondition
from app.models.matching import AssetMatchingResult
from app.services.asset_matching_service import classify_band, confirm_matching_result, run_matching

from tests.conftest import make_asset, make_request, set_default_scoring_settings


def test_scenario1_full_match_idle_asset_scores_high(db_session):
    set_default_scoring_settings(db_session)
    make_request(db_session)
    make_asset(
        db_session, "SC-MAR-TRUCK-2026-00001",
        asset_subclass="VEHICLE", asset_type="Xe tải",
        asset_status="Đang nhàn rỗi", capacity_design=5, capacity_utilized=0,
        technical_specification="Xe tải 5 tấn, động cơ diesel, đã kiểm định.",
        province_city="Bình Dương",
    )

    results = run_matching(db_session, "ASR-202611-00001")

    assert len(results) == 1
    result = results[0]
    assert result.asset_id == "SC-MAR-TRUCK-2026-00001"
    assert result.score_total >= 85  # đủ dữ liệu + đáp ứng mọi tiêu chí -> phù hợp cao
    assert result.suitability_band == "HIGH"
    # Không bao giờ tự động kết luận đủ điều kiện điều chuyển.
    assert result.confirmed_status == "PENDING_CONFIRMATION"


def test_scenario2_insufficient_capacity_scores_lower(db_session):
    set_default_scoring_settings(db_session)
    make_request(db_session, requested_capacity=5)
    make_asset(
        db_session, "SC-DGL-TRUCK-2026-00001",
        asset_subclass="VEHICLE", asset_type="Xe tải",
        asset_status="Đang khai thác đủ công suất",
        capacity_design=10, capacity_utilized=9.5,  # chỉ còn dư 0.5, cần 5
    )

    results = run_matching(db_session, "ASR-202611-00001")

    assert len(results) == 1
    assert results[0].score_capacity < 7.5  # dưới 50% điểm công suất tối đa (15)
    assert "không đủ" in results[0].rationale


def test_scenario3_needs_repair_scores_lower_on_condition_and_cost(db_session):
    set_default_scoring_settings(db_session)
    make_request(db_session)
    make_asset(
        db_session, "SC-MAR-FORKLIFT-2026-00001",
        asset_subclass="VEHICLE", asset_type="Xe tải",
        asset_status="Đang sửa chữa/bảo trì", capacity_design=5, capacity_utilized=0,
    )
    db_session.add(AssetCondition(
        inspection_id="INS-TEST-01", asset_id="SC-MAR-FORKLIFT-2026-00001",
        inspection_date=dt.date(2026, 10, 1), maintenance_required=True,
        can_be_transferred=False, estimated_repair_cost=15_000_000, estimated_downtime_days=10,
    ))
    db_session.flush()

    results = run_matching(db_session, "ASR-202611-00001")

    assert len(results) == 1
    result = results[0]
    assert result.score_condition <= 0.3 * 15  # hệ số 0.3 trên trọng số condition=15
    assert "cần sửa chữa" in result.rationale
    assert result.suitability_band != "HIGH"


def test_scenario4_no_matching_asset_returns_empty_and_no_rows_persisted(db_session):
    set_default_scoring_settings(db_session)
    make_request(db_session, asset_group="Tàu biển")  # không có tài sản nhóm này trong DB

    results = run_matching(db_session, "ASR-202611-00001")

    assert results == []
    assert db_session.query(AssetMatchingResult).count() == 0


def test_rerun_matching_replaces_previous_results(db_session):
    set_default_scoring_settings(db_session)
    make_request(db_session)
    make_asset(db_session, "SC-MAR-TRUCK-2026-00001", capacity_design=5, capacity_utilized=0)

    run_matching(db_session, "ASR-202611-00001")
    first_count = db_session.query(AssetMatchingResult).count()
    run_matching(db_session, "ASR-202611-00001")
    second_count = db_session.query(AssetMatchingResult).count()

    assert first_count == 1
    assert second_count == 1  # không tích lũy trùng lặp qua các lần chạy lại


def test_classify_band_thresholds_are_configurable():
    thresholds = {"high_fit": 90, "needs_review": 75}
    assert classify_band(95, thresholds) == "HIGH"
    assert classify_band(80, thresholds) == "NEEDS_REVIEW"
    assert classify_band(50, thresholds) == "LOW_PRIORITY"


def test_run_matching_raises_for_unknown_request(db_session):
    with pytest.raises(ValueError):
        run_matching(db_session, "ASR-NOT-EXIST")


def custodian_ctx() -> UserContext:
    return UserContext(user_id="cust_seagull01", full_name="Custodian", roles=("ASSET_CUSTODIAN",),
                        scoped_companies=("SEAGULL_MARINE",))


def requester_ctx() -> UserContext:
    return UserContext(user_id="req_danny01", full_name="Requester", roles=("REQUESTING_UNIT",),
                        scoped_companies=("DANNYGREEN",))


def test_scenario7_owner_refuses_transfer_requires_reason(db_session):
    """Kịch bản 7 — đơn vị sở hữu tài sản từ chối điều chuyển."""
    set_default_scoring_settings(db_session)
    make_request(db_session)
    make_asset(db_session, "SC-MAR-TRUCK-2026-00001", capacity_design=5, capacity_utilized=0)
    results = run_matching(db_session, "ASR-202611-00001")
    best = results[0]

    with pytest.raises(ValueError):
        confirm_matching_result(db_session, best.id, custodian_ctx(), accepted=False, comments=None)

    rejected = confirm_matching_result(
        db_session, best.id, custodian_ctx(), accepted=False,
        comments="Đơn vị đang khai thác xe cho kế hoạch sản xuất khác, không đồng ý bàn giao.",
    )
    assert rejected.confirmed_status == "REJECTED_BY_REVIEWER"
    assert rejected.confirmed_by == "cust_seagull01"
    assert "không đồng ý bàn giao" in rejected.rationale


def test_confirm_matching_result_requires_authorized_role(db_session):
    set_default_scoring_settings(db_session)
    make_request(db_session)
    make_asset(db_session, "SC-MAR-TRUCK-2026-00001", capacity_design=5, capacity_utilized=0)
    results = run_matching(db_session, "ASR-202611-00001")
    best = results[0]

    with pytest.raises(PermissionDenied):
        confirm_matching_result(db_session, best.id, requester_ctx(), accepted=True, comments="Tôi tự xác nhận")
