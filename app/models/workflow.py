"""State machine mục VIII: NEW -> ... -> CLOSED. Không tự động đóng hồ sơ
nếu chưa có xác nhận của người chịu trách nhiệm."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import Date, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base

WORKFLOW_STATES = [
    "NEW", "RECEIVED", "AI_ANALYZING", "NEED_MORE_INFORMATION", "ASSET_MATCHING",
    "MATCH_FOUND", "NO_MATCH", "NEED_TECHNICAL_REVIEW",
    "TRANSFER_REVIEW", "PROCUREMENT_REVIEW", "ACCOUNTING_REVIEW", "ASSET_MANAGEMENT_REVIEW",
    "PENDING_APPROVAL", "APPROVED", "REJECTED",
    "TRANSFER_EXECUTION", "PROCUREMENT_EXECUTION", "HANDOVER_COMPLETED", "CLOSED",
]


class WorkflowTask(Base):
    __tablename__ = "workflow_tasks"

    task_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    request_id: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(40), nullable=False)
    assigned_role: Mapped[str] = mapped_column(String(50), nullable=False)
    assigned_to: Mapped[str | None] = mapped_column(String(100))

    due_date: Mapped[dt.date | None] = mapped_column(Date)
    started_at: Mapped[dt.datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[dt.datetime | None] = mapped_column(DateTime)

    attachments: Mapped[str | None] = mapped_column(Text)
    comments: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="OPEN")  # OPEN/DONE/OVERDUE/CANCELLED

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False)


class ApprovalHistory(Base):
    __tablename__ = "approval_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    task_id: Mapped[str | None] = mapped_column(String(40))

    from_state: Mapped[str | None] = mapped_column(String(40))
    to_state: Mapped[str] = mapped_column(String(40), nullable=False)

    approver_role: Mapped[str] = mapped_column(String(50), nullable=False)
    approver_id: Mapped[str] = mapped_column(String(100), nullable=False)
    decision: Mapped[str] = mapped_column(String(30), nullable=False)  # APPROVED/REJECTED/RETURNED/CONFIRMED
    comments: Mapped[str | None] = mapped_column(Text)
    decided_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False)
