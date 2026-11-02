"""Hash mật khẩu + RBAC helpers. Không hard-code secret thật trong code.

Dùng trực tiếp thư viện `bcrypt` (không qua passlib) — passlib 1.7.x dò sai
backend với bcrypt>=4.1 (thiếu `__about__`), gây lỗi khi hash.
"""
from __future__ import annotations

import bcrypt

from app.models.auth import ROLES


def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def is_valid_role(role_code: str) -> bool:
    return role_code in ROLES
