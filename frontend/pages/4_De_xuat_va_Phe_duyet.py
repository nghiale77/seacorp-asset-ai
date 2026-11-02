from __future__ import annotations

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st  # noqa: E402

from app.core.rbac import PermissionDenied  # noqa: E402
from app.core.timeutils import utcnow  # noqa: E402
from app.models.matching import AssetMatchingResult  # noqa: E402
from app.models.proposal import ProcurementProposal, TransferProposal  # noqa: E402
from app.models.request import AssetRequest  # noqa: E402
from app.models.workflow import ApprovalHistory  # noqa: E402
from app.services.workflow_service import TRANSITIONS, InvalidTransition, transition  # noqa: E402
from frontend.auth import require_login  # noqa: E402
from frontend.db import get_db_session  # noqa: E402

st.set_page_config(page_title="Đề xuất & Phê duyệt", page_icon="📝", layout="wide")
ctx = require_login()
st.title("📝 Bước 4 — Đề xuất xử lý & Phê duyệt")

db = get_db_session()
try:
    requests = (
        db.query(AssetRequest)
        .filter(~AssetRequest.status.in_(["NEW", "RECEIVED", "AI_ANALYZING", "NEED_MORE_INFORMATION", "ASSET_MATCHING", "CLOSED"]))
        .order_by(AssetRequest.updated_at.desc())
        .all()
    )
    if not requests:
        st.info("Chưa có hồ sơ nào ở giai đoạn đề xuất/phê duyệt (cần chạy đối chiếu tài sản trước ở trang 3).")
    else:
        options = {r.request_id: f"{r.request_id} — {r.status}" for r in requests}
        selected_id = st.selectbox("Chọn hồ sơ", options=list(options.keys()), format_func=lambda k: options[k])
        request = db.get(AssetRequest, selected_id)
        st.write(f"**Trạng thái hiện tại:** `{request.status}`")

        transfer = db.query(TransferProposal).filter_by(request_id=request.request_id).first()
        procurement = db.query(ProcurementProposal).filter_by(request_id=request.request_id).first()

        tab1, tab2, tab3 = st.tabs(["TRƯỜNG HỢP A — Điều chuyển", "TRƯỜNG HỢP B — Mua sắm mới", "Chuyển trạng thái"])

        with tab1:
            best_match = (
                db.query(AssetMatchingResult).filter_by(request_id=request.request_id)
                .order_by(AssetMatchingResult.score_total.desc()).first()
            )
            if transfer:
                st.write(f"Đề xuất điều chuyển tài sản **{transfer.asset_id}** — trạng thái `{transfer.status}`")
                st.json({
                    "net_book_value": float(transfer.net_book_value) if transfer.net_book_value else None,
                    "equivalent_new_purchase_cost": float(transfer.equivalent_new_purchase_cost) if transfer.equivalent_new_purchase_cost else None,
                    "transfer_cost_estimate": float(transfer.transfer_cost_estimate) if transfer.transfer_cost_estimate else None,
                    "repair_upgrade_cost_estimate": float(transfer.repair_upgrade_cost_estimate) if transfer.repair_upgrade_cost_estimate else None,
                })
            elif best_match:
                st.write(f"Lập đề xuất điều chuyển cho tài sản ứng viên tốt nhất: **{best_match.asset_id}**")
                with st.form("transfer_form"):
                    nbv = st.number_input("Giá trị còn lại (VNĐ)", min_value=0.0, step=1_000_000.0)
                    equiv = st.number_input("Giá trị mua mới tương đương (VNĐ)", min_value=0.0, step=1_000_000.0)
                    tcost = st.number_input("Chi phí điều chuyển ước tính (VNĐ)", min_value=0.0, step=100_000.0)
                    rcost = st.number_input("Chi phí sửa chữa/nâng cấp ước tính (VNĐ)", min_value=0.0, step=100_000.0)
                    benefit = st.text_area("Đánh giá lợi ích so với mua mới")
                    risk = st.text_area("Rủi ro kỹ thuật/vận hành")
                    if st.form_submit_button("Tạo đề xuất điều chuyển"):
                        db.add(TransferProposal(
                            proposal_id=f"TP-{uuid.uuid4().hex[:10]}", request_id=request.request_id,
                            asset_id=best_match.asset_id, net_book_value=nbv or None,
                            equivalent_new_purchase_cost=equiv or None, transfer_cost_estimate=tcost or None,
                            repair_upgrade_cost_estimate=rcost or None, benefit_vs_new_purchase=benefit or None,
                            operational_technical_risk=risk or None, status="DRAFT", created_at=utcnow(),
                        ))
                        db.commit()
                        st.rerun()
            else:
                st.caption("Chưa có kết quả đối chiếu tài sản cho hồ sơ này.")

        with tab2:
            if procurement:
                st.write(f"Đề xuất mua sắm — trạng thái `{procurement.status}`, phương án đề xuất: "
                         f"**{procurement.recommended_option or 'chưa chọn'}**")
                st.json({
                    "option_buy_new_cost": float(procurement.option_buy_new_cost) if procurement.option_buy_new_cost else None,
                    "option_rent_cost": float(procurement.option_rent_cost) if procurement.option_rent_cost else None,
                    "option_use_existing_cost": float(procurement.option_use_existing_cost) if procurement.option_use_existing_cost else None,
                })
            else:
                with st.form("procurement_form"):
                    scope = st.text_area("Phạm vi dữ liệu đã tìm kiếm")
                    reasons = st.text_area("Lý do không phù hợp")
                    buy = st.number_input("Chi phí mua mới (VNĐ)", min_value=0.0, step=1_000_000.0)
                    rent = st.number_input("Chi phí thuê (VNĐ/kỳ)", min_value=0.0, step=1_000_000.0)
                    use_existing = st.number_input("Chi phí tận dụng tài sản hiện có (VNĐ)", min_value=0.0, step=1_000_000.0)
                    recommended = st.selectbox("Phương án đề xuất", ["Mua mới", "Thuê tài sản", "Sử dụng/điều chuyển tài sản hiện có"])
                    rationale = st.text_area("Lý giải đề xuất")
                    if st.form_submit_button("Tạo đề xuất mua sắm (BM-02)"):
                        db.add(ProcurementProposal(
                            proposal_id=f"PP-{uuid.uuid4().hex[:10]}", request_id=request.request_id,
                            search_scope_summary=scope or None, reasons_not_suitable=reasons or None,
                            option_buy_new_cost=buy or None, option_rent_cost=rent or None,
                            option_use_existing_cost=use_existing or None, recommended_option=recommended,
                            recommendation_rationale=rationale or None, status="DRAFT", created_at=utcnow(),
                        ))
                        db.commit()
                        st.rerun()

        with tab3:
            allowed_next = TRANSITIONS.get(request.status, [])
            if not allowed_next:
                st.caption("Hồ sơ đã ở trạng thái cuối, không còn bước chuyển tiếp.")
            else:
                next_state = st.selectbox("Chuyển sang trạng thái", options=allowed_next)
                comments = st.text_area(
                    "Ý kiến xử lý / xác nhận",
                    help="Bắt buộc với APPROVED/REJECTED/TRANSFER_EXECUTION→HANDOVER_COMPLETED/CLOSED.",
                )
                if st.button("Thực hiện chuyển trạng thái"):
                    try:
                        transition(db, request.request_id, next_state, ctx, comments=comments or None)
                        db.commit()
                        st.success(f"Đã chuyển sang {next_state}.")
                        st.rerun()
                    except (InvalidTransition, PermissionDenied, ValueError) as exc:
                        st.error(str(exc))

            st.divider()
            st.subheader("Lịch sử phê duyệt")
            history = (
                db.query(ApprovalHistory).filter_by(request_id=request.request_id)
                .order_by(ApprovalHistory.decided_at).all()
            )
            if history:
                st.dataframe([
                    {"Thời gian": h.decided_at.strftime("%d/%m/%Y %H:%M"), "Từ": h.from_state, "Đến": h.to_state,
                     "Người thực hiện": h.approver_id, "Vai trò": h.approver_role, "Ý kiến": h.comments or ""}
                    for h in history
                ], use_container_width=True, hide_index=True)
            else:
                st.caption("Chưa có lịch sử chuyển trạng thái.")
finally:
    db.close()
