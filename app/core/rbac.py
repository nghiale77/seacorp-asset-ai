"""RBAC: phạm vi xem dữ liệu theo vai trò + đơn vị (mục PHÂN QUYỀN NGƯỜI DÙNG).

Vai trò quản trị/toàn hệ thống (QLTS&ĐT, System Admin, Management Viewer) xem
toàn bộ dữ liệu. Các vai trò còn lại chỉ xem dữ liệu của company_code mà họ
được gán (`UserRoleAssignment.scope_company_code`); không được xem hồ sơ tài
chính/báo giá của đơn vị khác nếu không được phân quyền.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.auth import UserRoleAssignment

GLOBAL_SCOPE_ROLES = {"SYSTEM_ADMIN", "ASSET_MGMT_ADMIN", "MANAGEMENT_VIEWER"}

# Vai trò được phép ra quyết định phê duyệt cuối cùng trên workflow.
APPROVAL_ROLES = {"APPROVER"}


@dataclass(frozen=True)
class UserContext:
    user_id: str
    full_name: str
    roles: tuple[str, ...]
    scoped_companies: tuple[str, ...]  # company_code cụ thể được gán; rỗng nếu có vai trò global

    @property
    def has_global_scope(self) -> bool:
        return bool(GLOBAL_SCOPE_ROLES & set(self.roles))

    def can_view_company(self, company_code: str | None) -> bool:
        if self.has_global_scope:
            return True
        if company_code is None:
            return False
        return company_code in self.scoped_companies

    def has_role(self, role_code: str) -> bool:
        return role_code in self.roles

    def can_approve(self) -> bool:
        return bool(APPROVAL_ROLES & set(self.roles))


def load_user_context(db: Session, user_id: str, full_name: str) -> UserContext:
    assignments = db.query(UserRoleAssignment).filter(UserRoleAssignment.user_id == user_id).all()
    roles = tuple(sorted({a.role_code for a in assignments}))
    scoped_companies = tuple(sorted({a.scope_company_code for a in assignments if a.scope_company_code}))
    return UserContext(user_id=user_id, full_name=full_name, roles=roles, scoped_companies=scoped_companies)


class PermissionDenied(Exception):
    pass


def require_role(ctx: UserContext, *allowed_roles: str) -> None:
    if not any(ctx.has_role(r) for r in allowed_roles):
        raise PermissionDenied(
            f"Người dùng '{ctx.user_id}' không có vai trò thuộc {allowed_roles}; "
            f"vai trò hiện có: {ctx.roles}."
        )


def require_company_access(ctx: UserContext, company_code: str | None) -> None:
    if not ctx.can_view_company(company_code):
        raise PermissionDenied(
            f"Người dùng '{ctx.user_id}' không được phân quyền xem dữ liệu của đơn vị '{company_code}'."
        )
