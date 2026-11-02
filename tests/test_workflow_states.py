"""Kiểm thử workflow_service — state machine, RBAC, cảnh báo quá hạn.
Bám các kịch bản: (8) hồ sơ vượt thời hạn xử lý, (9) người không có thẩm
quyền cố gắng phê duyệt; đồng thời xác minh "không tự động đóng hồ sơ nếu
chưa có xác nhận của người chịu trách nhiệm".
"""
from __future__ import annotations

import datetime as dt

import pytest

from app.core.rbac import PermissionDenied, UserContext
from app.models.workflow import ApprovalHistory, WorkflowTask
from app.services.workflow_service import (
    InvalidTransition,
    list_overdue_tasks,
    mark_overdue_tasks,
    transition,
)

from tests.conftest import make_request


def admin_ctx() -> UserContext:
    return UserContext(user_id="qlts01", full_name="QLTS Admin", roles=("ASSET_MGMT_ADMIN",), scoped_companies=())


def approver_ctx() -> UserContext:
    return UserContext(user_id="approver01", full_name="Approver", roles=("APPROVER",), scoped_companies=())


def requester_ctx() -> UserContext:
    return UserContext(user_id="req_danny01", full_name="Requester", roles=("REQUESTING_UNIT",),
                        scoped_companies=("DANNYGREEN",))


def test_valid_transition_new_to_received(db_session):
    make_request(db_session, status="NEW")
    req = transition(db_session, "ASR-202611-00001", "RECEIVED", admin_ctx())
    assert req.status == "RECEIVED"
    history = db_session.query(ApprovalHistory).filter_by(request_id="ASR-202611-00001").all()
    assert len(history) == 1
    assert history[0].to_state == "RECEIVED"
    task = db_session.query(WorkflowTask).filter_by(request_id="ASR-202611-00001").first()
    assert task is not None
    assert task.state == "RECEIVED"
    assert task.status == "OPEN"


def test_invalid_transition_rejected(db_session):
    make_request(db_session, status="NEW")
    with pytest.raises(InvalidTransition):
        transition(db_session, "ASR-202611-00001", "APPROVED", admin_ctx())


def test_scenario9_unauthorized_user_cannot_approve(db_session):
    """Kịch bản 9 — người không có thẩm quyền cố gắng phê duyệt phải bị chặn."""
    from app.models.request import AssetRequest

    make_request(db_session, status="PENDING_APPROVAL")
    with pytest.raises(PermissionDenied):
        transition(db_session, "ASR-202611-00001", "APPROVED", requester_ctx(), comments="Tôi tự duyệt")

    req = db_session.get(AssetRequest, "ASR-202611-00001")
    assert req.status == "PENDING_APPROVAL"  # giữ nguyên, không bị chuyển trạng thái
    assert db_session.query(ApprovalHistory).filter_by(request_id="ASR-202611-00001").count() == 0


def test_authorized_approver_can_approve_with_confirmation(db_session):
    make_request(db_session, status="PENDING_APPROVAL")
    req = transition(db_session, "ASR-202611-00001", "APPROVED", approver_ctx(),
                      comments="Đã xem xét đầy đủ hồ sơ, phê duyệt điều chuyển.")
    assert req.status == "APPROVED"


def test_cannot_close_without_confirmation_comment(db_session):
    """'Không tự động đóng hồ sơ nếu chưa có xác nhận của người chịu trách nhiệm.'"""
    make_request(db_session, status="HANDOVER_COMPLETED")
    with pytest.raises(ValueError):
        transition(db_session, "ASR-202611-00001", "CLOSED", admin_ctx(), comments=None)

    # Có xác nhận hợp lệ thì đóng được.
    req = transition(db_session, "ASR-202611-00001", "CLOSED", admin_ctx(),
                      comments="Đã nhận đủ hồ sơ bàn giao, xác nhận đóng.")
    assert req.status == "CLOSED"


def test_scenario8_overdue_task_is_flagged_not_autoclosed(db_session):
    make_request(db_session, status="NEW")
    transition(db_session, "ASR-202611-00001", "RECEIVED", admin_ctx())

    task = db_session.query(WorkflowTask).filter_by(request_id="ASR-202611-00001").first()
    task.due_date = dt.date(2020, 1, 1)  # ép hồ sơ quá hạn
    db_session.flush()

    overdue = list_overdue_tasks(db_session, as_of=dt.date(2026, 11, 2))
    assert len(overdue) == 1

    count = mark_overdue_tasks(db_session, as_of=dt.date(2026, 11, 2))
    assert count == 1
    db_session.refresh(task)
    assert task.status == "OVERDUE"

    # Quá hạn chỉ là cảnh báo — hồ sơ vẫn ở RECEIVED, KHÔNG tự đóng/không tự chuyển trạng thái.
    from app.models.request import AssetRequest

    req = db_session.get(AssetRequest, "ASR-202611-00001")
    assert req.status == "RECEIVED"
