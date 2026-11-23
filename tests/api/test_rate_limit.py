from __future__ import annotations

from app.api.rate_limit import client_ip


def test_client_ip_uses_rightmost_forwarded_for_hop():
    """Spoofed leading X-Forwarded-For values must not bypass rate limits."""
    spoofed = "203.0.113.50, 198.51.100.10"
    assert client_ip(spoofed, "10.0.0.1") == "198.51.100.10"


def test_client_ip_single_hop_from_proxy():
    assert client_ip("198.51.100.10", "10.0.0.1") == "198.51.100.10"


def test_client_ip_falls_back_to_peer():
    assert client_ip(None, "10.0.0.1") == "10.0.0.1"
    assert client_ip("", None) == "unknown"
