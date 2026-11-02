from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st  # noqa: E402

from app.core.rbac import PermissionDenied  # noqa: E402
from app.models.asset import Asset  # noqa: E402
from app.models.matching import AssetMatchingResult  # noqa: E402
from app.models.request import AssetRequest  # noqa: E402
from app.services.asset_matching_service import confirm_matching_result, run_matching  # noqa: E402
from app.services.workflow_service import TRANSITIONS, InvalidTransition, transition  # noqa: E402
from frontend.auth import require_login  # noqa: E402
from frontend.db import get_db_session  # noqa: E402

st.set_page_config(page_title="Đối chiếu tài sản", page_icon="⚖️", layout="wide")
ctx = require_login()
st.title("⚖️ Bước 3 — Đối chiếu dữ liệu tài sản toàn hệ thống")
st.caption(
    "Chức năng quan trọng nhất của hệ thống. Kết quả LUÔN ở trạng thái đề xuất/chờ xác nhận — "
    "không tự động kết luận một tài sản đủ điều kiện điều chuyển chỉ dựa trên điểm số."
)

db = get_db_session()
try:
    requests = db.query(AssetRequest).filter(AssetRequest.status.in_(
        ["ASSET_MATCHING", "NEED_TECHNICAL_REVIEW", "MATCH_FOUND", "NO_MATCH"]
    )).order_by(AssetRequest.created_at.desc()).all()

    if not requests:
        st.info("Không có hồ sơ ở giai đoạn đối chiếu tài sản.")
    else:
        options = {r.request_id: f"{r.request_id} — {r.asset_group or '(chưa rõ nhóm)'} ({r.status})" for r in requests}
        selected_id = st.selectbox("Chọn hồ sơ", options=list(options.keys()), format_func=lambda k: options[k])
        request = db.get(AssetRequest, selected_id)

        st.write(f"Nhu cầu: **{request.asset_group or 'chưa rõ'}**, số lượng {request.requested_quantity or '?'}, "
                 f"công suất cần {request.requested_capacity or '?'}, địa điểm {request.requested_location_province or '?'}")

        if st.button("▶ Chạy đối chiếu tài sản"):
            results = run_matching(db, request.request_id)
            db.commit()
            st.success(f"Đã chấm điểm {len(results)} tài sản ứng viên.")
            st.rerun()

        results = (
            db.query(AssetMatchingResult)
            .filter_by(request_id=request.request_id)
            .order_by(AssetMatchingResult.score_total.desc())
            .all()
        )

        if results:
            band_color = {"HIGH": "🟢", "NEEDS_REVIEW": "🟡", "LOW_PRIORITY": "🔴"}
            rows = []
            for r in results:
                asset = db.get(Asset, r.asset_id)
                rows.append({
                    "": band_color.get(r.suitability_band, ""),
                    "Tài sản": f"{asset.asset_name} ({r.asset_id})" if asset else r.asset_id,
                    "Điểm": float(r.score_total), "Mức": r.suitability_band,
                    "Xác nhận": r.confirmed_status, "Ghi chú": r.rationale,
                })
            st.dataframe(rows, use_container_width=True, hide_index=True)

            st.divider()
            st.markdown("**Xác nhận kết quả (Đơn vị quản lý/Kỹ thuật/QLTS&ĐT) — bắt buộc trước khi điều chuyển**")
            best = results[0]
            asset_best = db.get(Asset, best.asset_id)
            st.write(f"Tài sản phù hợp cao nhất: **{asset_best.asset_name}** — điểm {float(best.score_total)} "
                     f"({best.suitability_band})")
            confirm_note = st.text_area(
                "Ý kiến xác nhận",
                placeholder="Xác nhận tình trạng/khả năng bàn giao thực tế, hoặc lý do từ chối "
                            "(ví dụ: đơn vị đang sở hữu/quản lý tài sản không đồng ý bàn giao)...",
            )
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Xác nhận phù hợp để điều chuyển"):
                    try:
                        confirm_matching_result(db, best.id, ctx, accepted=True, comments=confirm_note or None)
                        db.commit()
                        st.success("Đã ghi nhận xác nhận.")
                        st.rerun()
                    except (PermissionDenied, ValueError) as exc:
                        st.error(str(exc))
            with col2:
                if st.button("❌ Từ chối (đơn vị sở hữu không đồng ý / cần đánh giá thêm)"):
                    try:
                        confirm_matching_result(db, best.id, ctx, accepted=False, comments=confirm_note or None)
                        db.commit()
                        st.warning("Đã ghi nhận từ chối — cần chuyển kỹ thuật đánh giá thêm hoặc xem tài sản khác.")
                        st.rerun()
                    except (PermissionDenied, ValueError) as exc:
                        st.error(str(exc))

            st.divider()
            candidate_states = [s for s in ("MATCH_FOUND", "NO_MATCH", "NEED_TECHNICAL_REVIEW")
                                 if s in TRANSITIONS.get(request.status, [])]
            if candidate_states:
                st.markdown("**Chuyển bước tiếp theo (Phòng QLTS&ĐT)**")
                cols = st.columns(len(candidate_states))
                labels = {
                    "MATCH_FOUND": "→ MATCH_FOUND (có tài sản phù hợp)",
                    "NO_MATCH": "→ NO_MATCH (không có tài sản phù hợp)",
                    "NEED_TECHNICAL_REVIEW": "→ NEED_TECHNICAL_REVIEW (cần đánh giá thêm)",
                }
                for col, state in zip(cols, candidate_states):
                    with col:
                        if st.button(labels[state], key=f"go_{state}"):
                            try:
                                transition(db, request.request_id, state, ctx)
                                db.commit()
                                st.rerun()
                            except (InvalidTransition, PermissionDenied, ValueError) as exc:
                                st.error(str(exc))
            else:
                st.caption(f"Hồ sơ đã ở trạng thái `{request.status}` — xem tiếp ở trang Đề xuất & Phê duyệt.")
        else:
            st.info("Chưa có kết quả đối chiếu — bấm 'Chạy đối chiếu tài sản'.")
            if "NO_MATCH" in TRANSITIONS.get(request.status, []):
                if st.button("→ NO_MATCH (xác nhận không có tài sản nào trong hệ thống)"):
                    try:
                        transition(db, request.request_id, "NO_MATCH", ctx)
                        db.commit()
                        st.rerun()
                    except (InvalidTransition, PermissionDenied, ValueError) as exc:
                        st.error(str(exc))
finally:
    db.close()
