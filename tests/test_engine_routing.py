from __future__ import annotations

import sys
from pathlib import Path

import pytest

from backend.app import (
    Profile,
    ProfileIn,
    normalize_engine_name,
    validate_profile_for_launch,
    worker_command,
    environment_risks_for_profile,
)


def test_normalize_engine_aliases():
    assert normalize_engine_name(None) == "camoufox"
    assert normalize_engine_name("") == "camoufox"
    assert normalize_engine_name("firefox") == "camoufox"
    assert normalize_engine_name("Camoufox") == "camoufox"
    assert normalize_engine_name("chromium") == "chromium"
    assert normalize_engine_name("chrome") == "chromium"
    assert normalize_engine_name("playwright") == "chromium"


def test_profile_in_engine_default_and_channel():
    p = ProfileIn(name="x")
    assert p.engine == "camoufox"
    assert p.chromium_channel == ""
    c = ProfileIn(name="y", engine="chrome", chromium_channel="msedge")
    assert c.engine == "chromium"
    assert c.chromium_channel == "msedge"


def test_profile_in_rejects_bad_engine():
    with pytest.raises(Exception):
        ProfileIn(name="bad", engine="webkit")


def test_chromium_server_mode_blocked():
    profile = Profile(
        id="p1",
        name="c",
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
        engine="chromium",
        mode="server",
        os="windows",
    )
    errors = validate_profile_for_launch(profile)
    assert any("server" in e.lower() or "Chromium" in e for e in errors)


def test_worker_command_source_mode_routes_script(tmp_path: Path):
    runtime = tmp_path / "r.json"
    runtime.write_text("{}", encoding="utf-8")
    cmd_c = worker_command(runtime, engine="chromium")
    cmd_f = worker_command(runtime, engine="camoufox")
    assert cmd_c[-1] == str(runtime)
    assert cmd_f[-1] == str(runtime)
    # Source mode embeds worker script path (not frozen).
    if not getattr(sys, "frozen", False):
        assert "chromium_worker" in " ".join(cmd_c)
        assert "camoufox_worker" in " ".join(cmd_f)


def test_chromium_environment_risk_flag():
    profile = Profile(
        id="p1",
        name="c",
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
        engine="chromium",
        mode="browser",
        os="windows",
        headless=False,
        persistent_context=True,
        block_webrtc=True,
        webrtc_mode="disable",
        locale="en-US",
        timezone="America/New_York",
    )
    codes = {r["code"] for r in environment_risks_for_profile(profile)}
    # Phase C: backend-specific risk codes replace phase_a chromium flag
    assert (
        "engine_chromium_phase_c_patchright" in codes
        or "engine_chromium_playwright" in codes
        or "engine_chromium_phase_a" in codes
    )
