from __future__ import annotations

import datetime as dt
import threading
from collections import defaultdict

from app.api.settings import get_settings

_lock = threading.Lock()
_minute_hits: dict[str, list[dt.datetime]] = defaultdict(list)
_day_hits: dict[str, tuple[dt.date, int]] = {}


def client_ip(forwarded_for: str | None, peer: str | None) -> str:
    """Client IP behind a single trusted reverse proxy (ALB).

    ALB appends the real client address as the last X-Forwarded-For hop; earlier
    values may be spoofed by the client and must not be used for rate limiting.
    """
    if forwarded_for:
        hops = [p.strip() for p in forwarded_for.split(",") if p.strip()]
        if hops:
            return hops[-1]
    return peer or "unknown"


def rate_limited(ip: str) -> bool:
    settings = get_settings()
    now = dt.datetime.now(dt.UTC)
    with _lock:
        minute_window = [t for t in _minute_hits[ip] if (now - t).total_seconds() < 60]
        if len(minute_window) >= settings.rate_limit_per_minute:
            return True
        day, count = _day_hits.get(ip, (now.date(), 0))
        if day != now.date():
            count = 0
            day = now.date()
        if count >= settings.rate_limit_per_day:
            return True
        minute_window.append(now)
        _minute_hits[ip] = minute_window
        _day_hits[ip] = (day, count + 1)
    return False
