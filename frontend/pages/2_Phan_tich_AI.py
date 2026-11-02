from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.rbac import PermissionDenied  # noqa: E402
from app.models.request import AssetRequest  # noqa: E402
from app.services.ai_analysis_service import run_ai_analysis  # noqa: E402
from app.services.workflow_service import InvalidTransition, transition  # noqa: E402
from frontend.auth import require_login  # noqa: E402
from frontend.db import get_db_session  # noqa: E402

st.set_page_config(page_title="Phân tích AI", page_icon="🔎", layout="wide")
ctx = require_login()
st.title("🔎 Bước 2 — AI phân tích nhu cầu tài sản")

settings = get_settings()
if settings.ai_enabled:
    st.caption("Claude API đã được cấu hình (ANTHROPIC_API_KEY) — AI sẽ trích xuất trực tiếp từ nội dung gốc.")
else:
    st.caption(
        "⚠️ Chưa cấu hình ANTHROPIC_API_KEY — hệ thống dùng chế độ fallback thủ công, "
        "không tự suy diễn số liệu không có trong văn bản."
    )

db = get_db_session()
try:
    requests = db.query(AssetRequest).filter(AssetRequest.status.in_(
        ["NEW", "RECEIVED", "AI_ANALYZING", "NEED_MORE_INFORMATION"]
    )).order_by(AssetRequest.created_at.desc()).all()

    if not requests:
        st.info("Không có hồ sơ đang ở giai đoạn tiếp nhận/phân tích.")
    else:
        options = {r.request_id: f"{r.request_id} — {r.sender_name} ({r.status})" for r in requests}
        selected_id = st.selectbox("Chọn hồ sơ", options=list(options.keys()), format_func=lambda k: options[k])
        request = db.get(AssetRequest, selected_id)

        st.text_area("Nội dung gốc", value=request.original_content, height=120, disabled=True)

        col_a, col_b = st.columns([1, 2])
        with col_a:
            if request.status == "NEW":
                if st.button("Xác nhận tiếp nhận (NEW → RECEIVED)"):
                    try:
                        transition(db, request.request_id, "RECEIVED", ctx)
                        db.commit()
                        st.rerun()
                    except (InvalidTransition, PermissionDenied, ValueError) as exc:
                        st.error(str(exc))
            if request.status == "RECEIVED":
                if st.button("Chuyển sang phân tích AI"):
                    try:
                        transition(db, request.request_id, "AI_ANALYZING", ctx)
                        db.commit()
                        st.rerun()
                    except (InvalidTransition, PermissionDenied, ValueError) as exc:
                        st.error(str(exc))
            if request.status in ("AI_ANALYZING", "NEED_MORE_INFORMATION"):
                if st.button("▶ Chạy phân tích AI"):
                    run_ai_analysis(db, request.request_id)
                    db.commit()
                    st.rerun()

        if request.ai_completeness:
            st.divider()
            st.subheader("Kết quả phân tích")
            st.write("**Mức độ đầy đủ:**", request.ai_completeness)
            if request.suspected_duplicate:
                st.warning(f"Nghi trùng với hồ sơ {request.duplicate_of_request_id}.")
            st.write("**Ghi chú độ tin cậy:**", request.ai_confidence_note)

            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**A. Đơn vị đề xuất**")
                st.write(request.proposed_unit_info or "—")
                st.markdown("**B. Thông tin tài sản**")
                st.write(request.proposed_asset_info or "—")
            with c2:
                st.markdown("**C. Nhu cầu sử dụng**")
                st.write(request.proposed_usage_need or "—")
                st.markdown("**D. Hiệu quả sử dụng**")
                st.write(request.proposed_efficiency_info or "—")

            st.divider()
            st.markdown("**Trường có cấu trúc (có thể chỉnh tay trước khi đối chiếu tài sản)**")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                new_group = st.text_input("Nhóm tài sản", value=request.asset_group or "")
            with col2:
                new_qty = st.number_input("Số lượng", value=float(request.requested_quantity or 0), min_value=0.0)
            with col3:
                new_cap = st.number_input("Công suất cần", value=float(request.requested_capacity or 0), min_value=0.0)
            with col4:
                new_loc = st.text_input("Địa điểm", value=request.requested_location_province or "")
            if st.button("Lưu chỉnh sửa thủ công"):
                request.asset_group = new_group or None
                request.requested_quantity = new_qty or None
                request.requested_capacity = new_cap or None
                request.requested_location_province = new_loc or None
                db.commit()
                st.success("Đã lưu.")

            st.divider()
            if request.status == "AI_ANALYZING":
                st.caption(
                    "AI chỉ ĐỀ XUẤT phân loại; chuyên viên Phòng QLTS&ĐT quyết định bước tiếp theo "
                    "— đặc biệt cần thiết khi chạy ở chế độ fallback thủ công (chưa cấu hình AI)."
                )
                col_x, col_y = st.columns(2)
                with col_x:
                    if st.button("✅ Đủ thông tin → chuyển Đối chiếu tài sản",
                                  type="primary" if request.ai_completeness == "Đầy đủ" else "secondary"):
                        try:
                            transition(db, request.request_id, "ASSET_MATCHING", ctx)
                            db.commit()
                            st.rerun()
                        except (InvalidTransition, PermissionDenied, ValueError) as exc:
                            st.error(str(exc))
                with col_y:
                    if st.button("✉ Yêu cầu bổ sung thông tin",
                                  type="primary" if request.ai_completeness != "Đầy đủ" else "secondary"):
                        try:
                            transition(db, request.request_id, "NEED_MORE_INFORMATION", ctx)
                            db.commit()
                            st.rerun()
                        except (InvalidTransition, PermissionDenied, ValueError) as exc:
                            st.error(str(exc))
finally:
    db.close()
