"""Fixture DB độc lập (SQLite in-memory) cho mỗi test — không đụng tới
seacorp_asset_dev.db dùng khi chạy demo thủ công."""
from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.session import Base
import app.models  # noqa: F401  (đăng ký toàn bộ model vào Base.metadata)
from app.models.asset import Asset
from app.models.audit import SystemSetting
from app.models.request import AssetRequest


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


def make_request(db, request_id="ASR-202611-00001", **overrides) -> AssetRequest:
    defaults = dict(
        request_id=request_id, sender_name="Test Sender", sender_email="test@seacorp.local",
        company_code="DANNYGREEN", department_code="KHO_VAN_DANNYGREEN",
        received_at=dt.datetime(2026, 11, 1), channel="manual_intake",
        original_content="Nội dung yêu cầu test.", asset_group="Xe tải",
        requested_quantity=1, requested_capacity=5, requested_location_province="Bình Dương",
        needed_by_date=dt.date(2026, 12, 1),
        status="NEW", created_at=dt.datetime(2026, 11, 1),
    )
    defaults.update(overrides)
    req = AssetRequest(**defaults)
    db.add(req)
    db.flush()
    return req


def make_asset(db, asset_id, **overrides) -> Asset:
    defaults = dict(
        asset_id=asset_id, asset_name=asset_id, asset_class="TANGIBLE",
        asset_subclass="VEHICLE", asset_type="Xe tải",
        legal_entity_owner="SEAGULL_MARINE", owning_unit="SEAGULL_MARINE",
        asset_status="Đang nhàn rỗi", lifecycle_status="Nhàn rỗi",
        capacity_design=5, capacity_current=5, capacity_utilized=0,
        province_city="Bình Dương", country="Việt Nam",
    )
    defaults.update(overrides)
    asset = Asset(**defaults)
    db.add(asset)
    db.flush()
    return asset


def set_default_scoring_settings(db) -> None:
    import json
    db.add(SystemSetting(
        setting_key="asset_matching.scoring_weights",
        value=json.dumps({"DEFAULT": {
            "function": 25, "technical_spec": 20, "capacity": 15, "condition": 15,
            "time_readiness": 10, "cost": 10, "location": 5,
        }}),
    ))
    db.add(SystemSetting(
        setting_key="asset_matching.thresholds",
        value=json.dumps({"high_fit": 85, "needs_review": 70}),
    ))
    db.flush()
