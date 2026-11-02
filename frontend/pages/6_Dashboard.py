from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st  # noqa: E402

from app.models.org import Company  # noqa: E402
from app.models.request import AssetRequest  # noqa: E402
from app.services.reporting_service import export_bm01, export_bm02, get_dashboard_summary  # noqa: E402
from app.services.workflow_service import list_overdue_tasks  # noqa: E402
from frontend.auth import require_login  # noqa: E402
from frontend.db import get_db_session  # noqa: E402

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
ctx = require_login()
st.title("📊 Dashboard quản trị — Phòng Quản lý Tài sản & Đầu tư")

db = get_db_session()
try:
    companies = db.query(Company).all()
    company_filter = st.selectbox(
        "Lọc theo công ty", options=[None] + [c.company_code for c in companies],
        format_func=lambda c: "Toàn hệ thống" if c is None else next(x.company_name for x in companies if x.company_code == c),
    )

    summary = get_dashboard_summary(db, company_code=company_filter)

    row1 = st.columns(4)
    row1[0].metric("Tổng số yêu cầu", summary["total_requests"])
    row1[1].metric("Mới tiếp nhận", summary["new_requests"])
    row1[2].metric("Chờ bổ sung thông tin", summary["awaiting_more_info"])
    row1[3].metric("Chờ phê duyệt", summary["pending_approval"])

    row2 = st.columns(4)
    row2[0].metric("Theo hướng điều chuyển", summary["to_transfer_track"])
    row2[1].metric("Theo hướng mua sắm mới", summary["to_procurement_track"])
    fit = summary["fit_rate_existing_assets_pct"]
    row2[2].metric("Tỷ lệ đáp ứng bằng tài sản hiện có",
                    f"{fit}%" if fit is not None else "—")
    row2[3].metric("Hồ sơ quá hạn", summary["overdue_tasks"],
                    help="Chỉ là cảnh báo — không tự động đóng hồ sơ.")

    row3 = st.columns(2)
    row3[0].metric("Tổng giá trị mua mới dự kiến", f"{summary['total_procurement_value_estimated']:,.0f} đ")
    savings = summary["total_transfer_savings_confirmed"]
    row3[1].metric(
        "Giá trị tiết kiệm nhờ điều chuyển (đã phê duyệt)",
        f"{savings:,.0f} đ" if savings is not None else "Chưa đủ cơ sở đánh giá",
        help=f"Tính trên {summary['transfer_savings_sample_count']} hồ sơ đã có đủ dữ liệu định lượng và đã phê duyệt.",
    )

    st.divider()
    st.subheader("Phân bố theo trạng thái")
    if summary["by_status"]:
        st.bar_chart(summary["by_status"])
    else:
        st.caption("Chưa có dữ liệu.")

    st.divider()
    st.subheader("Hồ sơ quá hạn xử lý")
    overdue = list_overdue_tasks(db)
    if overdue:
        st.dataframe([
            {"Mã hồ sơ": t.request_id, "Trạng thái công việc": t.state, "Vai trò phụ trách": t.assigned_role,
             "Hạn xử lý": t.due_date.strftime("%d/%m/%Y"), "Trạng thái task": t.status}
            for t in overdue
        ], use_container_width=True, hide_index=True)
    else:
        st.caption("Không có hồ sơ quá hạn.")

    st.divider()
    st.subheader("Xuất biểu mẫu BM-01 / BM-02")
    all_requests = db.query(AssetRequest).order_by(AssetRequest.created_at.desc()).all()
    if all_requests:
        export_id = st.selectbox(
            "Chọn hồ sơ để xuất", options=[r.request_id for r in all_requests],
        )
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Xuất BM-01"):
                with tempfile.TemporaryDirectory() as tmp:
                    path = export_bm01(db, export_id, tmp)
                    st.download_button("⬇️ Tải BM-01.xlsx", data=path.read_bytes(), file_name=path.name)
        with col2:
            if st.button("Xuất BM-02"):
                with tempfile.TemporaryDirectory() as tmp:
                    path = export_bm02(db, export_id, tmp)
                    st.download_button("⬇️ Tải BM-02.xlsx", data=path.read_bytes(), file_name=path.name)
finally:
    db.close()
