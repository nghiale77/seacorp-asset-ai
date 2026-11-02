"""Bước 5 — phản hồi, luôn ở trạng thái chờ duyệt trước khi 'gửi' (xem lưu ý
cuối tài liệu: không bật tự động gửi email ngay từ đầu)."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class EmailMessage(Base):
    __tablename__ = "email_messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    template_code: Mapped[str] = mapped_column(String(30), nullable=False)  # M1..M5
    recipient: Mapped[str | None] = mapped_column(String(200))
    subject: Mapped[str] = mapped_column(String(300), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING_APPROVAL")
    # DRAFT / PENDING_APPROVAL / APPROVED / SENT / REJECTED / FAILED
    created_by: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(100))
    approved_at: Mapped[dt.datetime | None] = mapped_column(DateTime)
    sent_at: Mapped[dt.datetime | None] = mapped_column(DateTime)
    error_message: Mapped[str | None] = mapped_column(Text)


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    request_id: Mapped[str | None] = mapped_column(String(30), index=True)
    target_role: Mapped[str | None] = mapped_column(String(50))
    target_user: Mapped[str | None] = mapped_column(String(100))
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False)
