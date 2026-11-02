"""Kiểm thử reporting_service — KPI dashboard + xuất BM-01/BM-02."""
from __future__ import annotations

import datetime as dt

import openpyxl

from app.models.proposal import ProcurementProposal, TransferProposal
from app.services.reporting_service import export_bm01, export_bm02, get_dashboard_summary

from tests.conftest import make_request


def test_dashboard_counts_by_status(db_session):
    make_request(db_session, request_id="ASR-202611-00001", status="NEW")
    make_request(db_session, request_id="ASR-202611-00002", status="NEED_MORE_INFORMATION")
    make_request(db_session, request_id="ASR-202611-00003", status="PENDING_APPROVAL")

    summary = get_dashboard_summary(db_session)
    assert summary["total_requests"] == 3
    assert summary["new_requests"] == 1
    assert summary["awaiting_more_info"] == 1
    assert summary["pending_approval"] == 1


def test_fit_rate_kpi_computed_from_transfer_vs_procurement_tracks(db_session):
    make_request(db_session, request_id="ASR-202611-00001", status="MATCH_FOUND")
    make_request(db_session, request_id="ASR-202611-00002", status="NO_MATCH")

    summary = get_dashboard_summary(db_session)
    assert summary["fit_rate_existing_assets_pct"] == 50.0


def test_savings_kpi_only_counts_approved_and_quantified_transfers(db_session):
    make_request(db_session, request_id="ASR-202611-00001", status="APPROVED")
    db_session.add(TransferProposal(
        proposal_id="TP-0001", request_id="ASR-202611-00001", asset_id="SC-MAR-TRUCK-2026-00001",
        equivalent_new_purchase_cost=500_000_000, transfer_cost_estimate=20_000_000,
        repair_upgrade_cost_estimate=10_000_000, status="APPROVED", created_at=dt.datetime(2026, 11, 1),
    ))
    # Hồ sơ thứ hai chưa phê duyệt -> KHÔNG được tính vào tiết kiệm.
    make_request(db_session, request_id="ASR-202611-00002", status="TRANSFER_REVIEW")
    db_session.add(TransferProposal(
        proposal_id="TP-0002", request_id="ASR-202611-00002", asset_id="SC-MAR-TRUCK-2026-00002",
        equivalent_new_purchase_cost=300_000_000, transfer_cost_estimate=5_000_000,
        status="DRAFT", created_at=dt.datetime(2026, 11, 1),
    ))
    db_session.flush()

    summary = get_dashboard_summary(db_session)
    assert summary["transfer_savings_sample_count"] == 1
    assert summary["total_transfer_savings_confirmed"] == 500_000_000 - 20_000_000 - 10_000_000


def test_savings_kpi_none_when_no_quantified_data(db_session):
    make_request(db_session, status="APPROVED")
    summary = get_dashboard_summary(db_session)
    assert summary["total_transfer_savings_confirmed"] is None


def test_export_bm01_creates_readable_workbook(db_session, tmp_path):
    make_request(db_session, original_content="Nội dung gốc test BM-01.")
    path = export_bm01(db_session, "ASR-202611-00001", tmp_path)

    assert path.exists()
    wb = openpyxl.load_workbook(path)
    ws = wb["BM-01"]
    values = {ws.cell(r, 1).value: ws.cell(r, 2).value for r in range(3, 10)}
    assert values.get("Mã yêu cầu") == "ASR-202611-00001"


def test_export_bm02_uses_procurement_and_transfer_data(db_session, tmp_path):
    make_request(db_session, request_id="ASR-202611-00001")
    db_session.add(ProcurementProposal(
        proposal_id="PP-0001", request_id="ASR-202611-00001",
        option_buy_new_cost=400_000_000, option_rent_cost=50_000_000,
        recommended_option="Mua mới", recommendation_rationale="Không có tài sản phù hợp để điều chuyển.",
        status="DRAFT", created_at=dt.datetime(2026, 11, 1),
    ))
    db_session.flush()

    path = export_bm02(db_session, "ASR-202611-00001", tmp_path)
    assert path.exists()
    wb = openpyxl.load_workbook(path)
    ws = wb["BM-02"]
    found_buy_new_value = any(
        row[1] == 400_000_000 for row in ws.iter_rows(min_row=7, max_row=11, values_only=True)
    )
    assert found_buy_new_value
