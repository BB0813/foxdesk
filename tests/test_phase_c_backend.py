from __future__ import annotations

import pytest

from backend.app import (
    ProfileIn,
    normalize_chromium_backend_name,
    resolve_chromium_backend,
    environment_risks_for_profile,
    Profile,
)
from backend.chromium_worker import resolve_sync_playwright


def test_normalize_chromium_backend_aliases():
    assert normalize_chromium_backend_name(None) == "auto"
    assert normalize_chromium_backend_name("pw") == "playwright"
    assert normalize_chromium_backend_name("pr") == "patchright"
    assert normalize_chromium_backend_name("PATCHRIGHT") == "patchright"


def test_profile_in_default_backend_auto():
    p = ProfileIn(name="x", engine="chromium")
    assert p.chromium_backend == "auto"


def test_resolve_prefers_patchright_when_installed():
    # Environment in CI/dev may or may not have patchright; assert consistency.
    try:
        import patchright  # noqa: F401

        has_pr = True
    except Exception:
        has_pr = False
    try:
        import playwright  # noqa: F401

        has_pw = True
    except Exception:
        has_pw = False
    if has_pr:
        assert resolve_chromium_backend("auto") == "patchright"
        assert resolve_chromium_backend("patchright") == "patchright"
    elif has_pw:
        assert resolve_chromium_backend("auto") == "playwright"
    else:
        with pytest.raises(RuntimeError):
            resolve_chromium_backend("auto")


def test_resolve_sync_playwright_auto():
    factory, name = resolve_sync_playwright({"chromium_backend": "auto"})
    assert callable(factory)
    assert name in {"patchright", "playwright"}


def test_resolve_sync_playwright_explicit_playwright():
    factory, name = resolve_sync_playwright({"chromium_backend": "playwright"})
    assert name == "playwright"
    assert callable(factory)


def test_environment_risk_mentions_backend():
    p = Profile(
        id="p1",
        name="t",
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
        engine="chromium",
        mode="browser",
        os="windows",
        chromium_backend="playwright",
        headless=False,
    )
    codes = {r["code"] for r in environment_risks_for_profile(p)}
    assert "engine_chromium_playwright" in codes


def test_environment_risk_patchright_when_auto_and_installed():
    try:
        import patchright  # noqa: F401
    except Exception:
        pytest.skip("patchright not installed")
    p = Profile(
        id="p2",
        name="t2",
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
        engine="chromium",
        mode="browser",
        os="windows",
        chromium_backend="auto",
        headless=False,
    )
    codes = {r["code"] for r in environment_risks_for_profile(p)}
    assert "engine_chromium_phase_c_patchright" in codes
