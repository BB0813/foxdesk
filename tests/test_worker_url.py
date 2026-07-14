from __future__ import annotations

import pytest

from backend.camoufox_worker import validate_nav_url


def test_validate_nav_url_accepts_http() -> None:
    assert validate_nav_url("https://example.com/path") == "https://example.com/path"
    assert validate_nav_url("about:blank") == "about:blank"


def test_validate_nav_url_rejects_other_schemes() -> None:
    with pytest.raises(ValueError):
        validate_nav_url("file:///etc/passwd")
    with pytest.raises(ValueError):
        validate_nav_url("javascript:alert(1)")
