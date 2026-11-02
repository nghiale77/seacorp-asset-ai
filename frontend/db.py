"""Helper DB session cho Streamlit — mỗi lần script rerun mở session riêng,
không cache Session giữa các lần rerun (tránh stale/thread-safety issues)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database.session import SessionLocal  # noqa: E402


def get_db_session():
    return SessionLocal()
