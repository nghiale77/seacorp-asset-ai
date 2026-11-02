"""Mục VI (Dashboard) + sinh BM-01/BM-02 từ dữ liệu đã tiếp nhận.

KPI "giá trị tiết kiệm nhờ điều chuyển" CHỈ tính trên các TransferProposal đã
có equivalent_new_purchase_cost (giá trị mua mới tương đương) VÀ thuộc hồ sơ
đã ở trạng thái thực thi/hoàn tất (APPROVED trở đi) — không ghi nhận tiết
kiệm cho phương án chưa được phê duyệt/thực hiện, đúng nguyên tắc tài liệu.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import openpyxl
from openpyxl.cell.cell import MergedCell
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter
from sqlalchemy.orm import Session

from app.models.proposal import ProcurementProposal, TransferProposal
from app.models.request import AssetRequest
from app.services.workflow_service import list_overdue_tasks

EXECUTED_OR_LATER_STATES = {
    "APPROVED", "TRANSFER_EXECUTION", "PROCUREMENT_EXECUTION", "HANDOVER_COMPLETED", "CLOSED",
}
TRANSFER_TRACK_STATES = {
    "MATCH_FOUND", "TRANSFER_REVIEW", "ACCOUNTING_REVIEW", "ASSET_MANAGEMENT_REVIEW",
    "PENDING_APPROVAL", "APPROVED", "TRANSFER_EXECUTION", "HANDOVER_COMPLETED", "CLOSED",
}
PROCUREMENT_TRACK_STATES = {
    "NO_MATCH", "PROCUREMENT_REVIEW", "PROCUREMENT_EXECUTION",
}


def get_dashboard_summary(db: Session, company_code: str | None = None) -> dict:
    query = db.query(AssetRequest)
    if company_code:
        query = query.filter(AssetRequest.company_code == company_code)
    requests = query.all()

    total = len(requests)
    by_status: dict[str, int] = {}
    for r in requests:
        by_status[r.status] = by_status.get(r.status, 0) + 1

    transfer_track = sum(1 for r in requests if r.status in TRANSFER_TRACK_STATES)
    procurement_track = sum(1 for r in requests if r.status in PROCUREMENT_TRACK_STATES)
    eligible_for_kpi = transfer_track + procurement_track  # "yêu cầu đủ điều kiện xử lý"

    fit_rate = round((transfer_track / eligible_for_kpi) * 100, 1) if eligible_for_kpi else None

    overdue = list_overdue_tasks(db)

    procurement_total = (
        db.query(ProcurementProposal)
        .join(AssetRequest, AssetRequest.request_id == ProcurementProposal.request_id)
        .filter(ProcurementProposal.option_buy_new_cost.isnot(None))
    )
    if company_code:
        procurement_total = procurement_total.filter(AssetRequest.company_code == company_code)
    total_procurement_value = sum(
        float(p.option_buy_new_cost) for p in procurement_total.all()
    ) or 0.0

    transfer_proposals = (
        db.query(TransferProposal)
        .join(AssetRequest, AssetRequest.request_id == TransferProposal.request_id)
        .filter(AssetRequest.status.in_(EXECUTED_OR_LATER_STATES))
    )
    if company_code:
        transfer_proposals = transfer_proposals.filter(AssetRequest.company_code == company_code)

    total_savings = 0.0
    savings_count = 0
    for tp in transfer_proposals.all():
        if tp.equivalent_new_purchase_cost is None:
            continue  # chưa đủ cơ sở đánh giá — không suy diễn giá trị tiết kiệm
        savings = (
            float(tp.equivalent_new_purchase_cost)
            - float(tp.transfer_cost_estimate or 0)
            - float(tp.repair_upgrade_cost_estimate or 0)
        )
        total_savings += savings
        savings_count += 1

    return {
        "total_requests": total,
        "by_status": by_status,
        "new_requests": by_status.get("NEW", 0) + by_status.get("RECEIVED", 0),
        "analyzing": by_status.get("AI_ANALYZING", 0),
        "awaiting_more_info": by_status.get("NEED_MORE_INFORMATION", 0),
        "to_transfer_track": transfer_track,
        "to_procurement_track": procurement_track,
        "pending_approval": by_status.get("PENDING_APPROVAL", 0),
        "overdue_tasks": len(overdue),
        "fit_rate_existing_assets_pct": fit_rate,  # KPI: tỷ lệ đáp ứng bằng tài sản hiện có
        "total_procurement_value_estimated": total_procurement_value,
        "total_transfer_savings_confirmed": total_savings if savings_count else None,
        "transfer_savings_sample_count": savings_count,
    }


def _autosize(ws) -> None:
    for col_idx in range(1, ws.max_column + 1):
        letter = get_column_letter(col_idx)
        length = 10
        for row_idx in range(1, ws.max_row + 1):
            cell = ws.cell(row_idx, col_idx)
            if isinstance(cell, MergedCell) or cell.value is None:
                continue
            length = max(length, len(str(cell.value)))
        ws.column_dimensions[letter].width = min(max(length + 2, 12), 60)


def export_bm01(db: Session, request_id: str, output_dir: str | Path) -> Path:
    request = db.get(AssetRequest, request_id)
    if request is None:
        raise ValueError(f"Không tìm thấy yêu cầu {request_id}")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "BM-01"
    bold = Font(bold=True)

    ws["A1"] = "BM-01 – PHIẾU YÊU CẦU VÀ ĐỀ XUẤT NHU CẦU TÀI SẢN"
    ws["A1"].font = Font(bold=True, size=13)
    ws.merge_cells("A1:D1")

    rows = [
        ("Mã yêu cầu", request.request_id, "Ngày tạo", request.created_at.strftime("%d/%m/%Y")),
        ("Pháp nhân/đơn vị đề xuất", request.company_code or "", "Người đề xuất", request.sender_name),
        ("Phòng/đơn vị", request.department_code or "", "Người dự kiến chịu trách nhiệm",
         request.assigned_responsible_person or ""),
        ("Nhóm tài sản", request.asset_group or "", "Số lượng", request.requested_quantity or ""),
        ("Địa điểm sử dụng", request.requested_location_province or "", "Thời điểm cần",
         request.needed_by_date.strftime("%d/%m/%Y") if request.needed_by_date else ""),
        ("Thời hạn/công suất cần", request.requested_capacity or "", "Ngân sách tối đa",
         request.max_budget or ""),
        ("Kênh tiếp nhận", request.channel, "Trạng thái hiện tại", request.status),
    ]
    r = 3
    for a, b, c, d in rows:
        ws.cell(r, 1, a).font = bold
        ws.cell(r, 2, b)
        ws.cell(r, 3, c).font = bold
        ws.cell(r, 4, d)
        r += 1

    r += 1
    ws.cell(r, 1, "A. Giải trình nhu cầu (trích nội dung gốc)").font = bold
    r += 1
    ws.cell(r, 1, request.original_content)
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=4)
    ws.cell(r, 1).alignment = Alignment(wrap_text=True, vertical="top")
    ws.row_dimensions[r].height = 80
    r += 2

    ws.cell(r, 1, "Phân tích AI (nếu có)").font = bold
    r += 1
    for label, value in [
        ("Thông tin đơn vị đề xuất", request.proposed_unit_info),
        ("Thông tin tài sản", request.proposed_asset_info),
        ("Nhu cầu sử dụng", request.proposed_usage_need),
        ("Hiệu quả sử dụng", request.proposed_efficiency_info),
        ("Mức độ đầy đủ", request.ai_completeness),
        ("Ghi chú độ tin cậy", request.ai_confidence_note),
    ]:
        ws.cell(r, 1, label).font = bold
        ws.cell(r, 2, value or "")
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=4)
        r += 1

    r += 1
    ws.cell(r, 1, "B. Xác nhận điện tử").font = bold
    r += 1
    for col, header in enumerate(["Vai trò", "Xác nhận/Nội dung", "Trạng thái hệ thống"], start=1):
        ws.cell(r, col, header).font = bold
    confirmations = [
        ("Người đề xuất", "Cam kết thông tin đúng và đầy đủ", "Chờ xác nhận"),
        ("Người đứng đầu đơn vị", "Xác nhận nhu cầu và người chịu trách nhiệm", "Chờ duyệt"),
        ("Phòng QLTS&ĐT", "Kết quả rà soát danh mục/tài sản nhàn rỗi", "Chờ xử lý"),
        ("Cấp phê duyệt", "Quyết định theo ma trận phân quyền", "Chờ phê duyệt"),
    ]
    for role, note, state in confirmations:
        r += 1
        ws.cell(r, 1, role)
        ws.cell(r, 2, note)
        ws.cell(r, 3, state)

    _autosize(ws)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"BM01_{request_id}.xlsx"
    wb.save(out_path)
    return out_path


def export_bm02(db: Session, request_id: str, output_dir: str | Path) -> Path:
    request = db.get(AssetRequest, request_id)
    if request is None:
        raise ValueError(f"Không tìm thấy yêu cầu {request_id}")

    transfer = db.query(TransferProposal).filter_by(request_id=request_id).first()
    procurement = db.query(ProcurementProposal).filter_by(request_id=request_id).first()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "BM-02"
    bold = Font(bold=True)

    ws["A1"] = "BM-02 – BẢNG ĐÁNH GIÁ PHƯƠNG ÁN MUA – THUÊ – ĐIỀU CHUYỂN – SỬ DỤNG TÀI SẢN HIỆN CÓ"
    ws["A1"].font = Font(bold=True, size=12)
    ws.merge_cells("A1:E1")

    ws.cell(3, 1, "Mã yêu cầu").font = bold
    ws.cell(3, 2, request.request_id)
    ws.cell(3, 3, "Tên tài sản/nhu cầu").font = bold
    ws.cell(3, 4, request.asset_group or "")
    ws.cell(4, 1, "Đơn vị sử dụng").font = bold
    ws.cell(4, 2, request.department_code or "")
    ws.cell(4, 3, "Thời gian cần").font = bold
    ws.cell(4, 4, request.needed_by_date.strftime("%d/%m/%Y") if request.needed_by_date else "")

    header_row = 6
    headers = ["Tiêu chí", "Mua mới", "Thuê", "Sử dụng tài sản hiện có", "Điều chuyển"]
    for col, h in enumerate(headers, start=1):
        ws.cell(header_row, col, h).font = bold

    buy = procurement.option_buy_new_cost if procurement else None
    rent = procurement.option_rent_cost if procurement else None
    use_existing = procurement.option_use_existing_cost if procurement else None
    transfer_cost = transfer.transfer_cost_estimate if transfer else None
    repair_cost = transfer.repair_upgrade_cost_estimate if transfer else None

    data_rows = [
        ("Chi phí đầu tư/ban đầu", buy, None, None, None),
        ("Tiền thuê/chi phí thuê", None, rent, None, None),
        ("Chi phí sử dụng tài sản hiện có", None, None, use_existing, None),
        ("Chi phí điều chuyển", None, None, None, transfer_cost),
        ("Chi phí sửa chữa/nâng cấp (nếu điều chuyển)", None, None, None, repair_cost),
    ]
    r = header_row
    for label, c1, c2, c3, c4 in data_rows:
        r += 1
        ws.cell(r, 1, label)
        ws.cell(r, 2, c1 if c1 is not None else "")
        ws.cell(r, 3, c2 if c2 is not None else "")
        ws.cell(r, 4, c3 if c3 is not None else "")
        ws.cell(r, 5, c4 if c4 is not None else "")

    r += 2
    ws.cell(r, 1, "Phương án đề xuất").font = bold
    recommended = procurement.recommended_option if procurement else (
        "Điều chuyển" if transfer else "Chưa đủ cơ sở đánh giá"
    )
    ws.cell(r, 2, recommended)
    r += 1
    ws.cell(r, 1, "Lý giải").font = bold
    rationale = (
        (procurement.recommendation_rationale if procurement else None)
        or (transfer.benefit_vs_new_purchase if transfer else None)
        or "Chưa đủ cơ sở đánh giá"
    )
    ws.cell(r, 2, rationale)
    ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=5)

    _autosize(ws)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"BM02_{request_id}.xlsx"
    wb.save(out_path)
    return out_path
