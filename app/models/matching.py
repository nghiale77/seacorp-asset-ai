"""Kết quả đối chiếu tài sản — Bước 3, chức năng quan trọng nhất của hệ thống."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class AssetMatchingResult(Base):
    __tablename__ = "asset_matching_results"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    asset_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    score_function: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    score_technical_spec: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    score_capacity: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    score_condition: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    score_time_readiness: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    score_cost: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    score_location: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    score_total: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)

    # "Đề xuất" — KHÔNG phải kết luận tự động đủ điều kiện điều chuyển.
    suitability_band: Mapped[str] = mapped_column(String(30), nullable=False)  # HIGH / NEEDS_REVIEW / LOW_PRIORITY
    rationale: Mapped[str | None] = mapped_column(Text)

    evaluated_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False)
    evaluated_by: Mapped[str] = mapped_column(String(50), default="system_matching_engine")
    confirmed_status: Mapped[str] = mapped_column(String(30), default="PENDING_CONFIRMATION")
    confirmed_by: Mapped[str | None] = mapped_column(String(100))
    confirmed_at: Mapped[dt.datetime | None] = mapped_column(DateTime)
