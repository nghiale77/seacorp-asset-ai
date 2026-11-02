"""Bước 4 — Trường hợp A (điều chuyển) và Trường hợp B (mua sắm mới)."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import Date, DateTime, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class TransferProposal(Base):
    """TRƯỜNG HỢP A — đề xuất điều chuyển tài sản hiện có."""

    __tablename__ = "transfer_proposals"

    proposal_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    request_id: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    asset_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    from_unit: Mapped[str | None] = mapped_column(String(100))
    to_unit: Mapped[str | None] = mapped_column(String(100))
    asset_condition_summary: Mapped[str | None] = mapped_column(Text)
    remaining_capacity: Mapped[float | None] = mapped_column(Numeric(18, 3))
    net_book_value: Mapped[float | None] = mapped_column(Numeric(20, 2))
    # Giá trị mua mới tương đương được tránh — dùng để tính KPI tiết kiệm; để
    # trống nếu chưa có cơ sở, KHÔNG suy diễn (xem reporting_service).
    equivalent_new_purchase_cost: Mapped[float | None] = mapped_column(Numeric(20, 2))
    transfer_cost_estimate: Mapped[float | None] = mapped_column(Numeric(20, 2))
    repair_upgrade_cost_estimate: Mapped[float | None] = mapped_column(Numeric(20, 2))
    estimated_handover_date: Mapped[dt.date | None] = mapped_column(Date)
    benefit_vs_new_purchase: Mapped[str | None] = mapped_column(Text)
    operational_technical_risk: Mapped[str | None] = mapped_column(Text)

    status: Mapped[str] = mapped_column(String(40), nullable=False, default="DRAFT")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[dt.datetime | None] = mapped_column(DateTime)


class ProcurementProposal(Base):
    """TRƯỜNG HỢP B — xác nhận không có tài sản phù hợp + đề xuất đầu tư (BM-02)."""

    __tablename__ = "procurement_proposals"

    proposal_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    request_id: Mapped[str] = mapped_column(String(30), nullable=False, index=True)

    search_scope_summary: Mapped[str | None] = mapped_column(Text)
    assets_checked: Mapped[str | None] = mapped_column(Text)
    reasons_not_suitable: Mapped[str | None] = mapped_column(Text)
    near_matches: Mapped[str | None] = mapped_column(Text)
    transfer_feasibility_conclusion: Mapped[str | None] = mapped_column(Text)

    # Tối thiểu 3 phương án — không mặc định mua mới là tốt nhất.
    option_buy_new_cost: Mapped[float | None] = mapped_column(Numeric(20, 2))
    option_rent_cost: Mapped[float | None] = mapped_column(Numeric(20, 2))
    option_use_existing_cost: Mapped[float | None] = mapped_column(Numeric(20, 2))
    recommended_option: Mapped[str | None] = mapped_column(String(50))
    recommendation_rationale: Mapped[str | None] = mapped_column(Text)

    status: Mapped[str] = mapped_column(String(40), nullable=False, default="DRAFT")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[dt.datetime | None] = mapped_column(DateTime)
