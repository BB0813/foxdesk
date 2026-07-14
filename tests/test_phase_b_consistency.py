from __future__ import annotations

from backend.app import Profile, ProxyConfig, environment_risks_for_profile, validate_profile_for_launch
from backend.chromium_worker import build_fingerprint_init_script


def _profile(**kwargs) -> Profile:
    data = dict(
        id="p1",
        name="t",
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
        mode="browser",
        engine="chromium",
        os="windows",
        headless=False,
        persistent_context=True,
        block_webrtc=True,
        webrtc_mode="disable",
        locale="en-US",
        timezone="America/New_York",
        consistency_policy="normal",
    )
    data.update(kwargs)
    return Profile(**data)


def test_strict_blocks_headless():
    p = _profile(headless=True, consistency_policy="strict")
    errors = validate_profile_for_launch(p)
    assert any("[strict] headless" in e for e in errors)


def test_normal_allows_headless_with_risk_only():
    p = _profile(headless=True, consistency_policy="normal")
    errors = validate_profile_for_launch(p)
    assert not any("[strict] headless" in e for e in errors)
    codes = {r["code"] for r in environment_risks_for_profile(p)}
    assert "headless" in codes


def test_screen_pair_required():
    p = _profile(screen_width=1920, screen_height=0)
    errors = validate_profile_for_launch(p)
    assert any("screen_width" in e for e in errors)


def test_headless_chrome_ua_rejected():
    p = _profile(user_agent="Mozilla/5.0 HeadlessChrome/127.0.0.0")
    errors = validate_profile_for_launch(p)
    assert any("HeadlessChrome" in e for e in errors)


def test_init_script_emits_overrides():
    script = build_fingerprint_init_script(
        {
            "navigator_platform": "Win32",
            "hardware_concurrency": 8,
            "ua_ch_platform": "Windows",
            "ua_ch_mobile": False,
            "webgl_vendor": "Google Inc. (Intel)",
        }
    )
    assert script is not None
    assert "Win32" in script
    assert "hardwareConcurrency" in script
    assert "userAgentData" in script


def test_init_script_minimal_still_ensures_chrome():
    # Phase B always injects ensureChrome even with empty profile.
    script = build_fingerprint_init_script({})
    assert script is not None
    assert "chrome" in script
