"""Đăng nhập + RBAC cho giao diện Streamlit."""
from __future__ import annotations

import streamlit as st

from app.core.rbac import UserContext, load_user_context
from app.core.security import verify_password
from app.models.auth import UserAccount
from frontend.db import get_db_session

SESSION_KEY = "seacorp_user_ctx"


def login(user_id: str, password: str) -> UserContext | None:
    db = get_db_session()
    try:
        account = db.get(UserAccount, user_id)
        if account is None or not account.active_flag:
            return None
        if not verify_password(password, account.hashed_password):
            return None
        ctx = load_user_context(db, account.user_id, account.full_name)
        return ctx
    finally:
        db.close()


def current_user() -> UserContext | None:
    return st.session_state.get(SESSION_KEY)


def require_login() -> UserContext:
    ctx = current_user()
    if ctx is None:
        st.warning("Vui lòng đăng nhập ở trang chủ trước khi dùng chức năng này.")
        st.stop()
    return ctx


def logout() -> None:
    st.session_state.pop(SESSION_KEY, None)
