from __future__ import annotations

from backend.app import (
    Profile,
    detect_google_chrome_install,
    environment_risks_for_profile,
    system as system_endpoint,
)
from backend.templates_data import profile_templates
from backend.chromium_worker import build_fingerprint_init_script


def test_ai_workstation_template_exists():
    tpls = profile_templates()
    ai = next(t for t in tpls if t["id"] == "ai-workstation")
    p = ai["profile"]
    assert p["engine"] == "chromium"
    assert p["chromium_backend"] == "auto"
    assert p["headless"] is False
    assert p["persistent_context"] is True
    assert "ai" in p["tags"]
    assert "Warm-up checklist" in p["notes"] or "预热" in p["notes"] or "checklist" in p["notes"].lower()


def test_ai_tag_prefers_chromium_risk():
    p = Profile(
        id="a1",
        name="ai",
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
        engine="camoufox",
        mode="browser",
        os="windows",
        headless=False,
        tags=["ai", "chatgpt"],
    )
    codes = {r["code"] for r in environment_risks_for_profile(p)}
    assert "ai_scene_prefer_chromium" in codes


def test_detect_chrome_shape():
    info = detect_google_chrome_install()
    assert "installed" in info
    assert isinstance(info.get("paths"), list)


def test_system_exposes_chromium_stack():
    # FastAPI route function is plain callable in this app layout
    data = system_endpoint()
    assert data.get("app_version")
    assert "playwright_installed" in data
    assert "patchright_installed" in data
    assert "chromium_stack" in data
    assert "google_chrome" in data


def test_init_script_always_has_ua_ch_surface():
    script = build_fingerprint_init_script(
        {
            "os": "windows",
            "navigator_platform": "Win32",
            "media_devices": "random",
            "font_pack": "windows",
        }
    )
    assert script
    assert "userAgentData" in script
    assert "enumerateDevices" in script
