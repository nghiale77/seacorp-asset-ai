from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import datetime as dt  # noqa: E402

import streamlit as st  # noqa: E402

from app.integrations.manual_intake import submit_request  # noqa: E402
from app.models.org import Company  # noqa: E402
from app.models.request import AssetRequest  # noqa: E402
from frontend.auth import require_login  # noqa: E402
from frontend.db import get_db_session  # noqa: E402

st.set_page_config(page_title="Tiếp nhận yêu cầu", page_icon="📥", layout="wide")
ctx = require_login()
st.title("📥 Bước 1 — Tiếp nhận yêu cầu tài sản")
st.caption(
    "Giai đoạn 1 dùng kênh nhập liệu nội bộ (manual_intake) thay cho Outlook/Gmail/Teams thật "
    "— dán nguyên văn nội dung email/tin nhắn vào đây, hệ thống xử lý giống như nhận qua email."
)

db = get_db_session()
try:
    companies = db.query(Company).all()
    company_options = {c.company_code: c.company_name for c in companies}

    with st.form("intake_form"):
        col1, col2 = st.columns(2)
        with col1:
            sender_name = st.text_input("Người gửi *", value=ctx.full_name)
            sender_email = st.text_input("Email người gửi", value=f"{ctx.user_id}@seacorp.local")
            company_code = st.selectbox(
                "Đơn vị đề xuất",
                options=[None] + list(company_options.keys()),
                format_func=lambda c: "(chưa chọn)" if c is None else company_options[c],
            )
        with col2:
            asset_group = st.text_input("Nhóm tài sản (nếu biết)", placeholder="Ví dụ: Xe tải")
            requested_quantity = st.number_input("Số lượng cần", min_value=0.0, step=1.0, value=0.0)
            requested_capacity = st.number_input("Công suất/tải trọng cần", min_value=0.0, step=1.0, value=0.0)
            needed_by = st.date_input("Thời điểm cần", value=None)
            requested_location = st.text_input("Địa điểm sử dụng (tỉnh/thành)")

        original_content = st.text_area(
            "Nội dung yêu cầu (nguyên văn email/tin nhắn) *", height=180,
            placeholder="Kính đề nghị Phòng QLTS&ĐT xem xét cấp ...",
        )
        submitted = st.form_submit_button("Tiếp nhận hồ sơ")

    if submitted:
        if not sender_name.strip() or not original_content.strip():
            st.error("Cần nhập Người gửi và Nội dung yêu cầu.")
        else:
            request = submit_request(
                db, sender_name=sender_name.strip(), sender_email=sender_email.strip() or None,
                company_code=company_code, original_content=original_content.strip(),
                asset_group=asset_group.strip() or None, channel="manual_intake",
            )
            if requested_quantity:
                request.requested_quantity = requested_quantity
            if requested_capacity:
                request.requested_capacity = requested_capacity
            if requested_location.strip():
                request.requested_location_province = requested_location.strip()
            if isinstance(needed_by, dt.date):
                request.needed_by_date = needed_by
            db.commit()

            if request.suspected_duplicate:
                st.warning(
                    f"Hồ sơ **{request.request_id}** đã được tạo nhưng NGHI TRÙNG với hồ sơ "
                    f"**{request.duplicate_of_request_id}** (cùng người gửi, nội dung tương tự trong 30 ngày). "
                    "Phòng QLTS&ĐT cần xác nhận trước khi xử lý tiếp — hồ sơ KHÔNG bị tự động gộp."
                )
            else:
                st.success(f"Đã tiếp nhận hồ sơ **{request.request_id}**.")

    st.divider()
    st.subheader("Hồ sơ gần đây")
    recent = db.query(AssetRequest).order_by(AssetRequest.created_at.desc()).limit(20).all()
    if recent:
        st.dataframe(
            [
                {
                    "Mã hồ sơ": r.request_id, "Người gửi": r.sender_name, "Đơn vị": r.company_code,
                    "Trạng thái": r.status, "Nghi trùng": "Có" if r.suspected_duplicate else "",
                    "Ngày tạo": r.created_at.strftime("%d/%m/%Y %H:%M"),
                }
                for r in recent
            ],
            use_container_width=True, hide_index=True,
        )
    else:
        st.caption("Chưa có hồ sơ nào.")
finally:
    db.close()
