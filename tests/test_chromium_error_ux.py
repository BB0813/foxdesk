from __future__ import annotations

from backend.app import (
    Profile,
    chromium_install_hint,
    humanize_chromium_launch_error,
    validate_profile_for_launch,
)


def test_chromium_install_hint_patchright():
    h = chromium_install_hint("patchright")
    assert "patchright install chromium" in h


def test_humanize_missing_browser_binary():
    msg = humanize_chromium_launch_error(
        "Executable doesn't exist at .../chrome-win/chrome.exe",
        "patchright",
    )
    assert "patchright install chromium" in msg
    assert "Chromium browser binary missing" in msg


def test_humanize_chrome_channel():
    msg = humanize_chromium_launch_error(
        "Failed to launch chrome because channel is invalid",
        "playwright",
    )
    assert "chromium_channel=chrome" in msg or "Chrome" in msg


def test_validate_chrome_channel_without_install(monkeypatch):
    monkeypatch.setattr(
        "backend.app.detect_google_chrome_install",
        lambda: {"installed": False, "paths": []},
    )
    p = Profile(
        id="p1",
        name="t",
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
        engine="chromium",
        mode="browser",
        os="windows",
        headless=False,
        chromium_channel="chrome",
        chromium_backend="playwright",
    )
    errors = validate_profile_for_launch(p)
    assert any("chromium_channel=chrome" in e for e in errors)
