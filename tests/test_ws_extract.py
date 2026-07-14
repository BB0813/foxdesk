from __future__ import annotations

from backend.camoufox_worker import _extract_ws_endpoint


def test_extract_ws_url_direct() -> None:
    assert _extract_ws_endpoint("ws://127.0.0.1:9222/abc") == "ws://127.0.0.1:9222/abc"
    assert _extract_ws_endpoint('endpoint: "ws://localhost:1234/dev"') == "ws://localhost:1234/dev"


def test_extract_ws_from_label() -> None:
    line = "Playwright endpoint: ws://127.0.0.1:56123/"
    assert _extract_ws_endpoint(line) == "ws://127.0.0.1:56123/"


def test_extract_hostport_fallback() -> None:
    line = "listening on 127.0.0.1:45678 (playwright)"
    assert _extract_ws_endpoint(line) == "ws://127.0.0.1:45678"


def test_extract_none() -> None:
    assert _extract_ws_endpoint("hello world") is None
