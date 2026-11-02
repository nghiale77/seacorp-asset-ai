"""State machine mục VIII của tài liệu quy trình: NEW -> ... -> CLOSED.

Nguyên tắc bắt buộc tuân thủ (lấy trực tiếp từ tài liệu):
- Mỗi bước có người chịu trách nhiệm, thời hạn, ngày bắt đầu/hoàn thành, lịch sử (WorkflowTask).
- Không tự động đóng hồ sơ nếu chưa có xác nhận của người chịu trách nhiệm.
- Người không có thẩm quyền không được phê duyệt (RBAC theo APPROVAL_ROLES).
"""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy.orm import Session

from app.core.rbac import PermissionDenied, UserContext
from app.core.timeutils import utcnow
from app.models.audit import AuditLog
from app.models.request import AssetRequest
from app.models.workflow import WORKFLOW_STATES, ApprovalHistory, WorkflowTask

# Trạng thái kế tiếp hợp lệ cho từng trạng thái hiện tại.
TRANSITIONS: dict[str, list[str]] = {
    "NEW": ["RECEIVED"],
    "RECEIVED": ["AI_ANALYZING"],
    "AI_ANALYZING": ["NEED_MORE_INFORMATION", "ASSET_MATCHING"],
    "NEED_MORE_INFORMATION": ["AI_ANALYZING"],
    "ASSET_MATCHING": ["MATCH_FOUND", "NO_MATCH", "NEED_TECHNICAL_REVIEW"],
    "MATCH_FOUND": ["TRANSFER_REVIEW"],
    "NO_MATCH": ["PROCUREMENT_REVIEW"],
    "NEED_TECHNICAL_REVIEW": ["MATCH_FOUND", "NO_MATCH"],
    "TRANSFER_REVIEW": ["ACCOUNTING_REVIEW"],
    "PROCUREMENT_REVIEW": ["ACCOUNTING_REVIEW"],
    "ACCOUNTING_REVIEW": ["ASSET_MANAGEMENT_REVIEW"],
    "ASSET_MANAGEMENT_REVIEW": ["PENDING_APPROVAL"],
    "PENDING_APPROVAL": ["APPROVED", "REJECTED"],
    "APPROVED": ["TRANSFER_EXECUTION", "PROCUREMENT_EXECUTION"],
    "REJECTED": ["CLOSED"],
    "TRANSFER_EXECUTION": ["HANDOVER_COMPLETED"],
    "PROCUREMENT_EXECUTION": ["HANDOVER_COMPLETED"],
    "HANDOVER_COMPLETED": ["CLOSED"],
    "CLOSED": [],
}

assert set(TRANSITIONS.keys()) == set(WORKFLOW_STATES)

# Vai trò được phép thực hiện việc chuyển SANG trạng thái tương ứng.
TRANSITION_ROLES: dict[str, set[str]] = {
    "RECEIVED": {"ASSET_MGMT_ADMIN", "SYSTEM_ADMIN"},
    "AI_ANALYZING": {"ASSET_MGMT_ADMIN", "SYSTEM_ADMIN"},
    "NEED_MORE_INFORMATION": {"ASSET_MGMT_ADMIN"},
    "ASSET_MATCHING": {"ASSET_MGMT_ADMIN"},
    "MATCH_FOUND": {"ASSET_MGMT_ADMIN"},
    "NO_MATCH": {"ASSET_MGMT_ADMIN"},
    "NEED_TECHNICAL_REVIEW": {"ASSET_MGMT_ADMIN", "TECHNICAL_REVIEWER"},
    "TRANSFER_REVIEW": {"ASSET_MGMT_ADMIN"},
    "PROCUREMENT_REVIEW": {"ASSET_MGMT_ADMIN"},
    "ACCOUNTING_REVIEW": {"ASSET_MGMT_ADMIN", "ACCOUNTANT"},
    "ASSET_MANAGEMENT_REVIEW": {"ASSET_MGMT_ADMIN", "ACCOUNTANT"},
    "PENDING_APPROVAL": {"ASSET_MGMT_ADMIN"},
    "APPROVED": {"APPROVER"},
    "REJECTED": {"APPROVER"},
    "TRANSFER_EXECUTION": {"ASSET_MGMT_ADMIN", "ASSET_CUSTODIAN"},
    "PROCUREMENT_EXECUTION": {"ASSET_MGMT_ADMIN", "PROCUREMENT"},
    "HANDOVER_COMPLETED": {"ASSET_CUSTODIAN", "ASSET_MGMT_ADMIN"},
    "CLOSED": {"ASSET_MGMT_ADMIN"},
}

# Các trạng thái "đóng vòng đời" — bắt buộc phải có xác nhận (comments) của
# người chịu trách nhiệm, không được tự động đóng khi chưa có kết quả xử lý.
STATES_REQUIRING_CONFIRMATION = {"HANDOVER_COMPLETED", "CLOSED", "APPROVED", "REJECTED"}

DEFAULT_TASK_DUE_DAYS = 5
TASK_DUE_DAYS_BY_STATE = {
    "NEED_MORE_INFORMATION": 3,
    "PENDING_APPROVAL": 7,
}


class InvalidTransition(Exception):
    pass


def _assign_role_for_state(state: str) -> str:
    roles = TRANSITION_ROLES.get(state, {"ASSET_MGMT_ADMIN"})
    return sorted(roles)[0]


def transition(
    db: Session,
    request_id: str,
    to_state: str,
    ctx: UserContext,
    comments: str | None = None,
) -> AssetRequest:
    """Chuyển trạng thái hồ sơ, có kiểm tra hợp lệ trạng thái + RBAC + xác nhận."""
    request = db.get(AssetRequest, request_id)
    if request is None:
        raise ValueError(f"Không tìm thấy yêu cầu {request_id}")

    current_state = request.status
    allowed_next = TRANSITIONS.get(current_state, [])
    if to_state not in allowed_next:
        raise InvalidTransition(
            f"Không thể chuyển từ '{current_state}' sang '{to_state}'. "
            f"Trạng thái kế tiếp hợp lệ: {allowed_next}."
        )

    required_roles = TRANSITION_ROLES.get(to_state, set())
    if required_roles and not any(ctx.has_role(r) for r in required_roles):
        raise PermissionDenied(
            f"Người dùng '{ctx.user_id}' (vai trò: {ctx.roles}) không có thẩm quyền "
            f"chuyển hồ sơ {request_id} sang trạng thái '{to_state}' (yêu cầu: {sorted(required_roles)})."
        )

    if to_state in STATES_REQUIRING_CONFIRMATION and not (comments and comments.strip()):
        raise ValueError(
            f"Chuyển sang '{to_state}' bắt buộc phải có xác nhận/ý kiến của người chịu trách nhiệm "
            f"(comments không được để trống) — không tự động đóng hồ sơ."
        )

    now = utcnow()

    # Đóng task đang mở (nếu có) ứng với trạng thái hiện tại.
    open_task = (
        db.query(WorkflowTask)
        .filter(WorkflowTask.request_id == request_id, WorkflowTask.state == current_state,
                WorkflowTask.status.in_(["OPEN", "OVERDUE"]))
        .first()
    )
    if open_task:
        open_task.status = "DONE"
        open_task.completed_at = now
        if comments:
            open_task.comments = comments

    db.add(ApprovalHistory(
        request_id=request_id, task_id=open_task.task_id if open_task else None,
        from_state=current_state, to_state=to_state,
        approver_role=_role_used(ctx, required_roles), approver_id=ctx.user_id,
        decision=to_state, comments=comments, decided_at=now,
    ))

    request.status = to_state
    request.updated_at = now

    # Mở task mới cho trạng thái kế tiếp, trừ khi là trạng thái cuối (CLOSED).
    if to_state != "CLOSED":
        due_days = TASK_DUE_DAYS_BY_STATE.get(to_state, DEFAULT_TASK_DUE_DAYS)
        db.add(WorkflowTask(
            task_id=f"WT-{uuid.uuid4().hex[:12]}", request_id=request_id, state=to_state,
            assigned_role=_assign_role_for_state(to_state),
            due_date=(now + dt.timedelta(days=due_days)).date(),
            started_at=now, status="OPEN", created_at=now,
        ))

    db.add(AuditLog(
        entity_type="asset_requests", entity_id=request_id, action="STATE_TRANSITION",
        actor=ctx.user_id, before_value=current_state, after_value=to_state,
        reason=comments, created_at=now,
    ))

    db.flush()
    return request


def _role_used(ctx: UserContext, required_roles: set[str]) -> str:
    if not required_roles:
        return ctx.roles[0] if ctx.roles else "UNKNOWN"
    matched = [r for r in ctx.roles if r in required_roles]
    return matched[0] if matched else (ctx.roles[0] if ctx.roles else "UNKNOWN")


def list_overdue_tasks(db: Session, as_of: dt.date | None = None) -> list[WorkflowTask]:
    """Cảnh báo hồ sơ quá hạn — CHỈ để cảnh báo, không tự động thay đổi trạng thái."""
    as_of = as_of or utcnow().date()
    return (
        db.query(WorkflowTask)
        .filter(WorkflowTask.status == "OPEN", WorkflowTask.due_date < as_of)
        .all()
    )


def mark_overdue_tasks(db: Session, as_of: dt.date | None = None) -> int:
    """Gắn cờ status=OVERDUE cho task quá hạn còn mở (không đóng hồ sơ)."""
    tasks = list_overdue_tasks(db, as_of)
    for task in tasks:
        task.status = "OVERDUE"
    db.flush()
    return len(tasks)
