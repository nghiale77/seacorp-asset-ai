"""Kiểm thử notification_service — luôn chờ duyệt trước khi gửi; kịch bản
(10) gửi trùng hoặc lỗi kết nối."""
from __future__ import annotations

import pytest

from app.core.rbac import PermissionDenied, UserContext
from app.integrations.logging_channel import FailingOutboundChannel, LoggingOutboundChannel
from app.services.notification_service import approve_notification, draft_notification, send_notification

from tests.conftest import make_request


def admin_ctx():
    return UserContext(user_id="qlts01", full_name="QLTS Admin", roles=("ASSET_MGMT_ADMIN",), scoped_companies=())


def approver_ctx():
    return UserContext(user_id="approver01", full_name="Approver", roles=("APPROVER",), scoped_companies=())


def test_draft_notification_starts_pending_approval(db_session):
    make_request(db_session)
    msg = draft_notification(db_session, "ASR-202611-00001", "M1", created_by="system")
    assert msg.status == "PENDING_APPROVAL"
    assert "ASR-202611-00001" in msg.body


def test_m3_requires_asset_context_fields(db_session):
    make_request(db_session)
    with pytest.raises(ValueError):
        draft_notification(db_session, "ASR-202611-00001", "M3", created_by="system")


def test_cannot_send_before_approval(db_session):
    make_request(db_session)
    msg = draft_notification(db_session, "ASR-202611-00001", "M1", created_by="system")
    with pytest.raises(ValueError):
        send_notification(db_session, msg.id, LoggingOutboundChannel())


def test_m3_approval_requires_approver_role_not_admin(db_session):
    make_request(db_session)
    msg = draft_notification(
        db_session, "ASR-202611-00001", "M3", created_by="system",
        asset_name="Xe tải cảng 5 tấn", asset_id="SC-MAR-TRUCK-2026-00001", asset_unit="Seagull Marine",
    )
    with pytest.raises(PermissionDenied):
        approve_notification(db_session, msg.id, admin_ctx(), approve=True)

    approved = approve_notification(db_session, msg.id, approver_ctx(), approve=True)
    assert approved.status == "APPROVED"


def test_m1_approval_by_asset_mgmt_admin_then_send_succeeds(db_session):
    make_request(db_session)
    msg = draft_notification(db_session, "ASR-202611-00001", "M1", created_by="system")
    approve_notification(db_session, msg.id, admin_ctx(), approve=True)

    sent = send_notification(db_session, msg.id, LoggingOutboundChannel())
    assert sent.status == "SENT"
    assert sent.sent_at is not None


def test_scenario10_duplicate_send_is_rejected(db_session):
    make_request(db_session)
    msg = draft_notification(db_session, "ASR-202611-00001", "M1", created_by="system")
    approve_notification(db_session, msg.id, admin_ctx(), approve=True)
    send_notification(db_session, msg.id, LoggingOutboundChannel())

    with pytest.raises(ValueError):
        send_notification(db_session, msg.id, LoggingOutboundChannel())


def test_scenario10_connection_failure_marks_failed_not_sent(db_session):
    make_request(db_session)
    msg = draft_notification(db_session, "ASR-202611-00001", "M1", created_by="system")
    approve_notification(db_session, msg.id, admin_ctx(), approve=True)

    result = send_notification(db_session, msg.id, FailingOutboundChannel("Mất kết nối SMTP"))
    assert result.status == "FAILED"
    assert "Mất kết nối" in result.error_message

    # Sau lỗi, vẫn có thể thử gửi lại (không bị khóa vĩnh viễn như trường hợp đã SENT).
    retried = send_notification(db_session, msg.id, LoggingOutboundChannel())
    assert retried.status == "SENT"
