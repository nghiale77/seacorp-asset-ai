"""UTC datetime helper — tránh dt.datetime.utcnow() đã deprecated, giữ naive
datetime để khớp với các cột DateTime hiện có trong model."""
from __future__ import annotations

import datetime as dt


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
