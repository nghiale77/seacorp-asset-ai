"""Hồ sơ yêu cầu tài sản — Bước 1 (tiếp nhận) trong tài liệu nghiệp vụ."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import Date, DateTime, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class AssetRequest(Base):
    """Mã ASR-YYYYMM-XXXXX; mỗi hồ sơ là một yêu cầu tài sản duy nhất."""

    __tablename__ = "asset_requests"

    request_id: Mapped[str] = mapped_column(String(30), primary_key=True)  # ASR-YYYYMM-XXXXX

    sender_name: Mapped[str] = mapped_column(String(200), nullable=False)
    sender_email: Mapped[str | None] = mapped_column(String(200))
    company_code: Mapped[str | None] = mapped_column(String(30))
    department_code: Mapped[str | None] = mapped_column(String(30))

    received_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False)
    channel: Mapped[str] = mapped_column(String(30), nullable=False, default="manual_intake")

    original_content: Mapped[str] = mapped_column(Text, nullable=False)
    asset_group: Mapped[str | None] = mapped_column(String(50))

    # Trường nhu cầu có cấu trúc, dùng làm input cho asset_matching_service — do
    # chuyên viên nhập tay hoặc do AI trích xuất (Bước 2); để NULL nếu chưa đủ dữ
    # liệu, KHÔNG suy diễn.
    requested_quantity: Mapped[float | None] = mapped_column(Numeric(18, 3))
    requested_capacity: Mapped[float | None] = mapped_column(Numeric(18, 3))
    requested_location_province: Mapped[str | None] = mapped_column(String(100))
    needed_by_date: Mapped[dt.date | None] = mapped_column(Date)
    max_budget: Mapped[float | None] = mapped_column(Numeric(20, 2))

    # Trường trích xuất bởi AI (Bước 2) — null nếu chưa đủ cơ sở, không suy diễn.
    proposed_unit_info: Mapped[str | None] = mapped_column(Text)
    proposed_asset_info: Mapped[str | None] = mapped_column(Text)
    proposed_usage_need: Mapped[str | None] = mapped_column(Text)
    proposed_efficiency_info: Mapped[str | None] = mapped_column(Text)
    ai_completeness: Mapped[str | None] = mapped_column(String(30))  # Đầy đủ/Thiếu thông tin/Không rõ mục đích/Trùng yêu cầu
    ai_confidence_note: Mapped[str | None] = mapped_column(Text)

    duplicate_of_request_id: Mapped[str | None] = mapped_column(String(30))
    suspected_duplicate: Mapped[bool] = mapped_column(default=False)

    status: Mapped[str] = mapped_column(String(40), nullable=False, default="NEW")
    due_date: Mapped[dt.date | None] = mapped_column()
    assigned_responsible_person: Mapped[str | None] = mapped_column(String(100))

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[dt.datetime | None] = mapped_column(DateTime)


class RequestDocument(Base):
    __tablename__ = "request_documents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(String(300), nullable=False)
    file_link: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str | None] = mapped_column(String(50))
    uploaded_by: Mapped[str | None] = mapped_column(String(100))
    uploaded_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False)
