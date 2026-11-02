"""SeaCorp AI Asset Request & Allocation Management System — Streamlit MVP.

Trang chủ: đăng nhập + tổng quan vai trò. Các chức năng nghiệp vụ nằm trong
frontend/pages/ (Streamlit tự nhận diện làm multipage app).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st  # noqa: E402

from frontend.auth import SESSION_KEY, current_user, login, logout  # noqa: E402

st.set_page_config(page_title="SeaCorp Asset AI", page_icon="🗂️", layout="wide")

st.title("🗂️ SeaCorp AI Asset Request & Allocation Management System")
st.caption("Giai đoạn 1 – MVP · Phòng Quản lý Tài sản & Đầu tư SeaCorp")

ctx = current_user()

if ctx is None:
    st.subheader("Đăng nhập")
    with st.form("login_form"):
        user_id = st.text_input("Mã người dùng (ví dụ: qlts01)")
        password = st.text_input("Mật khẩu", type="password")
        submitted = st.form_submit_button("Đăng nhập")
    if submitted:
        result = login(user_id.strip(), password)
        if result is None:
            st.error("Sai mã người dùng hoặc mật khẩu, hoặc tài khoản không tồn tại.")
        else:
            st.session_state[SESSION_KEY] = result
            st.rerun()

    st.info(
        "Tài khoản demo (dữ liệu cục bộ, chạy `python scripts/seed_demo_data.py` trước): "
        "`qlts01`, `req_danny01`, `req_farm01`, `cust_seagull01`, `tech01`, `acct01`, `proc01`, "
        "`approver01`, `mgmt01`, `admin01` — mật khẩu `Demo@123`."
    )
else:
    st.success(f"Đã đăng nhập: **{ctx.full_name}** ({ctx.user_id})")
    st.write("Vai trò:", ", ".join(ctx.roles) or "(chưa gán vai trò)")
    if ctx.scoped_companies:
        st.write("Phạm vi đơn vị:", ", ".join(ctx.scoped_companies))
    elif ctx.has_global_scope:
        st.write("Phạm vi: toàn hệ thống SeaCorp")

    if st.button("Đăng xuất"):
        logout()
        st.rerun()

    st.divider()
    st.markdown(
        """
        ### Điều hướng (xem sidebar bên trái)
        1. **Tiếp nhận yêu cầu** — tạo hồ sơ ASR mới (Requesting Unit / QLTS&ĐT).
        2. **Phân tích AI** — chạy AI đọc nội dung, xem phân loại đầy đủ/thiếu thông tin/trùng.
        3. **Đối chiếu tài sản** — chạy thuật toán chấm điểm, xác nhận kết quả.
        4. **Đề xuất & Phê duyệt** — lập đề xuất điều chuyển/mua sắm, chuyển quy trình, phê duyệt.
        5. **Thông báo** — soạn/duyệt/gửi 5 mẫu email, không gửi tự động khi chưa duyệt.
        6. **Dashboard** — KPI, biểu đồ, xuất BM-01/BM-02.
        """
    )
