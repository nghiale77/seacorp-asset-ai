"""RBAC — 9 vai trò theo tài liệu, mục PHÂN QUYỀN NGƯỜI DÙNG."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base

ROLES = [
    "SYSTEM_ADMIN",             # System Admin
    "ASSET_MGMT_ADMIN",         # Asset Management Admin — Phòng QLTS&ĐT
    "REQUESTING_UNIT",          # Requesting Unit — đơn vị đề xuất
    "ASSET_CUSTODIAN",          # Asset Custodian — đơn vị đang quản lý/sử dụng
    "TECHNICAL_REVIEWER",       # Technical Reviewer
    "ACCOUNTANT",               # Accountant — Phòng Kế toán
    "PROCUREMENT",              # Procurement
    "APPROVER",                 # Approver — người có thẩm quyền phê duyệt
    "MANAGEMENT_VIEWER",        # Management Viewer — Ban TGĐ / lãnh đạo xem báo cáo
]


class UserAccount(Base):
    __tablename__ = "user_accounts"

    user_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(String(300), nullable=False)
    company_code: Mapped[str | None] = mapped_column(String(30))
    department_code: Mapped[str | None] = mapped_column(String(30))
    active_flag: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False)


class UserRoleAssignment(Base):
    """Gán vai trò + phạm vi dữ liệu (theo company_code) cho user — Requesting
    Unit không được xem hồ sơ của đơn vị khác nếu không được phân quyền."""

    __tablename__ = "user_role_assignments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    role_code: Mapped[str] = mapped_column(String(50), nullable=False)
    scope_company_code: Mapped[str | None] = mapped_column(String(30))  # None = toàn hệ thống (ví dụ QLTS&ĐT)
