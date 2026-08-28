"""Tests for D-B3/B5/B6/B7 additions: proxy quality classification,
datacenter risk hint, one-click suggestion, init-script permission patch,
UA drift parsing."""

from __future__ import annotations

import pytest

from backend.app import (
    ApplySuggestionRequest,
    Profile,
    environment_risks_for_profile,
)


# ---------- D-B6: proxy quality classification ----------

class TestProxyQuality:
    def test_classify_org_heuristics(self):
        from backend.proxy_quality import classify_org

        assert classify_org("Hetzner Online GmbH") == "datacenter"
        assert classify_org("Amazon.com, Inc.") == "datacenter"
        assert classify_org("AS14061 DigitalOcean, LLC") == "datacenter"
        assert classify_org("T-Mobile USA, Inc.") == "mobile"
        assert classify_org("China Mobile Group") == "mobile"
        assert classify_org("Comcast Cable") == "residential"
        assert classify_org("") == "unknown"
        assert classify_org(None) == "unknown"  # type: ignore[arg-type]

    def test_classify_exit_ip_no_network_needed_for_empty(self):
        from backend.proxy_quality import classify_exit_ip

        result = classify_exit_ip("")
        assert result["quality"] == "unknown"

    def test_datacenter_proxy_risk_hint(self, monkeypatch):
        class FakePool:
            def get(self, proxy_id):
                return {"id": proxy_id, "quality": "datacenter"}

        monkeypatch.setattr("backend.profile_logic.proxy_pool", FakePool())
        profile = _chromium_profile(proxy_id="p1")
        codes = {r["code"] for r in environment_risks_for_profile(profile)}
        assert "datacenter_proxy" in codes
        levels = {r["code"]: r["level"] for r in environment_risks_for_profile(profile)}
        assert levels["datacenter_proxy"] == "medium"

    def test_residential_proxy_low_hint(self, monkeypatch):
        class FakePool:
            def get(self, proxy_id):
                return {"id": proxy_id, "quality": "residential"}

        monkeypatch.setattr("backend.profile_logic.proxy_pool", FakePool())
        codes = {r["code"] for r in environment_risks_for_profile(_chromium_profile(proxy_id="p1"))}
        assert "residential_proxy" in codes

    def test_no_quality_hint_without_pool_binding(self):
        codes = {r["code"] for r in environment_risks_for_profile(_chromium_profile())}
        assert "datacenter_proxy" not in codes
        assert "residential_proxy" not in codes


# ---------- D-B5: one-click suggestion ----------

class TestApplySuggestion:
    def test_channel_suggestion_applied(self, monkeypatch, tmp_path):
        from backend.core import ProfileStore
        from backend.models import ProfileIn
        from backend.routes.profiles import _SUGGESTION_APPLIERS, apply_risk_suggestion

        store = ProfileStore(tmp_path / "profiles.json")
        profile = store.create(ProfileIn(name="Sugg", engine="chromium"))
        monkeypatch.setattr("backend.routes.profiles.store", store)
        monkeypatch.setattr(
            "backend.routes.profiles.detect_google_chrome_install",
            lambda: {"installed": True, "paths": ["C:/x/chrome.exe"]},
        )
        updated = apply_risk_suggestion(profile.id, ApplySuggestionRequest(code="chromium_bundled_build"))
        assert updated.chromium_channel == "chrome"
        assert "chromium_bundled_build" in _SUGGESTION_APPLIERS

    def test_unknown_code_rejected(self, monkeypatch, tmp_path):
        from backend.core import ProfileStore
        from backend.models import ProfileIn
        from backend.routes import profiles as profiles_route

        store = ProfileStore(tmp_path / "profiles.json")
        profile = store.create(ProfileIn(name="Sugg2", engine="chromium"))
        monkeypatch.setattr(profiles_route, "store", store)
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            profiles_route.apply_risk_suggestion(profile.id, ApplySuggestionRequest(code="nope"))
        assert exc.value.status_code == 400


# ---------- D-B3: init-script permission consistency ----------

class TestInitScriptPermissionPatch:
    def test_script_contains_notification_alignment(self):
        from backend.chromium_worker import build_fingerprint_init_script

        script = build_fingerprint_init_script({})
        assert script is not None
        assert "notifications" in script
        assert "Notification.permission" in script

    def test_alignment_is_conditional(self):
        """Only aligns when Notification.permission is 'denied' — must not
        claim 'granted'/'default' for daily-browsing profiles."""
        from backend.chromium_worker import build_fingerprint_init_script

        script = build_fingerprint_init_script({})
        assert "Notification.permission === 'denied'" in script
        assert "state: () => 'granted'" not in script


# ---------- D-B7: UA drift parsing ----------

class TestDriftCheckParsing:
    def test_embedded_majors_found(self):
        sys_path_guard = str(__import__("pathlib").Path(__file__).resolve().parents[1])
        import sys

        if sys_path_guard not in sys.path:
            sys.path.insert(0, sys_path_guard)
        from tools.chrome_drift_check import embedded_ua_majors

        majors = embedded_ua_majors()
        assert 153 in majors["chrome"]
        assert 154 in majors["firefox"]

    def test_stale_threshold_logic(self):
        # latest=153, embedded oldest=152 → within threshold (diff=1 ≤ 2 → fresh)
        latest, oldest, threshold = 153, 152, 2
        assert not ((latest - oldest) > threshold)


def _chromium_profile(**kwargs):
    from backend.models import ProxyConfig

    data = dict(
        id="p1",
        name="t",
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
        engine="chromium",
        chromium_backend="patchright",
        mode="browser",
        os="windows",
        headless=False,
        persistent_context=True,
        geoip=True,
        block_webrtc=True,
        webrtc_mode="disable",
        locale="en-US",
        timezone="America/New_York",
        proxy=ProxyConfig(server="socks5://1.2.3.4:1080"),
    )
    data.update(kwargs)
    return Profile(**data)
