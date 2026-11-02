"""Smoke test cho app/api/main.py — đảm bảo container `api` không crash khi
deploy (trước đây Dockerfile trỏ tới app.api.main:app nhưng file chưa tồn tại)."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.main import app


def test_health_check():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
