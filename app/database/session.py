"""SQLAlchemy engine/session setup.

Postgres (`seacorp_asset` schema) là mục tiêu triển khai thật theo kế hoạch,
nhưng môi trường build/test hiện tại không có Docker/Postgres sẵn, nên mặc
định dev/test dùng SQLite (xem .env.example). SQLite không hỗ trợ schema
riêng nên chỉ áp schema khi chạy trên Postgres.
"""
from __future__ import annotations

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy import create_engine

from app.core.config import get_settings

settings = get_settings()

SCHEMA = settings.db_schema if settings.is_postgres else None
metadata_obj = MetaData(schema=SCHEMA)


class Base(DeclarativeBase):
    metadata = metadata_obj


_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=_connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
