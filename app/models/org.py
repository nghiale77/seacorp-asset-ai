"""Danh mục pháp nhân / phòng ban / nhân sự."""
from __future__ import annotations

from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class Company(Base):
    __tablename__ = "companies"

    company_code: Mapped[str] = mapped_column(String(30), primary_key=True)
    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    legal_entity_type: Mapped[str | None] = mapped_column(String(50))
    industry: Mapped[str | None] = mapped_column(String(100))
    active_flag: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(String(500))


class Department(Base):
    __tablename__ = "departments"

    department_code: Mapped[str] = mapped_column(String(30), primary_key=True)
    department_name: Mapped[str] = mapped_column(String(200), nullable=False)
    company_code: Mapped[str] = mapped_column(String(30), nullable=False)
    parent_department_code: Mapped[str | None] = mapped_column(String(30))
    department_type: Mapped[str | None] = mapped_column(String(50))
    active_flag: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(String(500))


class Employee(Base):
    __tablename__ = "employees"

    employee_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    company_code: Mapped[str | None] = mapped_column(String(30))
    department_code: Mapped[str | None] = mapped_column(String(30))
    title: Mapped[str | None] = mapped_column(String(100))
    email: Mapped[str | None] = mapped_column(String(200))
    phone: Mapped[str | None] = mapped_column(String(50))
    active_flag: Mapped[bool] = mapped_column(Boolean, default=True)
