from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st  # noqa: E402

from app.core.rbac import PermissionDenied  # noqa: E402
from app.models.notification import EmailMessage  # noqa: E402
from app.models.request import AssetRequest  # noqa: E402
from app.integrations.logging_channel import LoggingOutboundChannel  # noqa: E402
from app.services.notification_service import (  # noqa: E402
    TEMPLATES,
    approve_notification,
    draft_notification,
    send_notification,
)
from frontend.auth import require_login  # noqa: E402
from frontend.db import get_db_session  # noqa: E402

st.set_page_config(page_title="Thông báo", page_icon="✉️", layout="wide")
ctx = require_login()
st.title("✉️ Bước 5 — Soạn, duyệt và gửi thông báo")
st.caption(
    "AI/chuyên viên chỉ SOẠN nội dung. Mọi thông báo phải qua duyệt trước khi 'gửi' — "
    "Giai đoạn 1 chưa nối Outlook/Gmail/Teams thật, 'gửi' = ghi nhận SENT + hiển thị tại đây."
)

db = get_db_session()
try:
    requests = db.query(AssetRequest).order_by(AssetRequest.created_at.desc()).limit(50).all()
    if requests:
        options = {r.request_id: f"{r.request_id} — {r.status}" for r in requests}
        selected_id = st.selectbox("Chọn hồ sơ", options=list(options.keys()), format_func=lambda k: options[k])
        request = db.get(AssetRequest, selected_id)

        with st.expander("Soạn thông báo mới"):
            template_code = st.selectbox("Mẫu", options=list(TEMPLATES.keys()),
                                          format_func=lambda c: f"{c} — {TEMPLATES[c]['required_context']}")
            context = {}
            if template_code == "M2":
                context["missing_fields"] = st.text_input("Danh sách thông tin còn thiếu")
            if template_code in ("M3",):
                context["asset_name"] = st.text_input("Tên tài sản")
                context["asset_id"] = st.text_input("Mã tài sản")
                context["asset_unit"] = st.text_input("Đơn vị đang quản lý")
            if st.button("Soạn thông báo"):
                try:
                    msg = draft_notification(db, request.request_id, template_code, created_by=ctx.user_id, **context)
                    db.commit()
                    st.success(f"Đã soạn thông báo #{msg.id} ({template_code}) — đang chờ duyệt.")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))

        st.divider()
        st.subheader(f"Thông báo của hồ sơ {request.request_id}")
        messages = db.query(EmailMessage).filter_by(request_id=request.request_id).order_by(EmailMessage.created_at).all()
        if not messages:
            st.caption("Chưa có thông báo nào.")
        for msg in messages:
            with st.container(border=True):
                st.write(f"**#{msg.id} · {msg.template_code} · {msg.status}** — gửi tới: {msg.recipient or '(chưa rõ)'}")
                st.write(f"*{msg.subject}*")
                st.write(msg.body)
                if msg.status == "PENDING_APPROVAL":
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Duyệt", key=f"approve_{msg.id}"):
                            try:
                                approve_notification(db, msg.id, ctx, approve=True)
                                db.commit()
                                st.rerun()
                            except PermissionDenied as exc:
                                st.error(str(exc))
                    with col2:
                        if st.button("❌ Từ chối", key=f"reject_{msg.id}"):
                            try:
                                approve_notification(db, msg.id, ctx, approve=False, comments="Từ chối qua UI")
                                db.commit()
                                st.rerun()
                            except PermissionDenied as exc:
                                st.error(str(exc))
                elif msg.status in ("APPROVED", "FAILED"):
                    if msg.status == "FAILED":
                        st.error(f"Lần gửi trước lỗi: {msg.error_message}")
                    if st.button("📤 Gửi", key=f"send_{msg.id}"):
                        result = send_notification(db, msg.id, LoggingOutboundChannel())
                        db.commit()
                        if result.status == "SENT":
                            st.success("Đã gửi.")
                        else:
                            st.error(f"Gửi thất bại: {result.error_message}")
                        st.rerun()
                elif msg.status == "SENT":
                    st.success(f"Đã gửi lúc {msg.sent_at.strftime('%d/%m/%Y %H:%M')}")
    else:
        st.info("Chưa có hồ sơ nào trong hệ thống.")
finally:
    db.close()
