from __future__ import annotations

from backend.fingerprint_presets import (
    FONT_PACKS,
    commercial_windows_desktop_hints,
    resolve_font_list,
    resolve_media_devices,
)
from backend.chromium_worker import build_fingerprint_init_script
from backend.app import Profile, environment_risks_for_profile


def test_font_pack_windows():
    fonts = resolve_font_list({"font_pack": "windows", "fonts": []})
    assert "Segoe UI" in fonts
    assert fonts == FONT_PACKS["windows"]


def test_explicit_fonts_win_over_pack():
    fonts = resolve_font_list({"font_pack": "windows", "fonts": ["CustomFont"]})
    assert fonts == ["CustomFont"]


def test_auto_pack_uses_os():
    fonts = resolve_font_list({"font_pack": "auto", "os": "macos", "fonts": []})
    assert "Helvetica" in fonts


def test_media_empty_and_random():
    mode, devices = resolve_media_devices({"media_devices": "empty"})
    assert mode == "empty"
    assert devices == []
    mode, devices = resolve_media_devices({"media_devices": "random"})
    assert mode == "random"
    assert devices and any(d["kind"] == "videoinput" for d in devices)


def test_init_script_includes_media_and_fonts():
    profile = commercial_windows_desktop_hints()
    script = build_fingerprint_init_script(profile)
    assert script is not None
    assert "enumerateDevices" in script
    assert "Segoe UI" in script or "fonts" in script
    assert "ensureChrome" in script or "window.chrome" in script


def test_chromium_fonts_unset_risk():
    p = Profile(
        id="p1",
        name="t",
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
        engine="chromium",
        mode="browser",
        os="windows",
        headless=False,
        fonts=[],
        font_pack="",
    )
    codes = {r["code"] for r in environment_risks_for_profile(p)}
    assert "fonts_unset" in codes


def test_bstatic_score_phase_b_gate():
    from tools.bstatic_probe import score_probe

    good = {
        "userAgent": "Mozilla/5.0 Chrome/127.0.0.0 Safari/537.36",
        "webdriver": True,  # expected until Phase C
        "hasChromeRuntime": True,
        "platform": "Win32",
        "languages": ["en-US"],
        "timezone": "America/New_York",
        "uaChBrands": [{"brand": "Chromium", "version": "127"}],
        "mediaDevices": {"count": 3},
        "fontsCheck": {"Arial": True},
        "pluginsLength": 0,
    }
    s = score_probe(good)
    assert s["phase_b_gate_ok"] is True
    assert s["phase_c_needed"] is True

    bad = dict(good)
    bad["userAgent"] = "Mozilla/5.0 HeadlessChrome/127.0.0.0 Safari/537.36"
    s2 = score_probe(bad)
    assert s2["phase_b_gate_ok"] is False
