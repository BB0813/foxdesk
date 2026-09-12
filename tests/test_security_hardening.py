"""Security hardening tests: restore path traversal, loopback Host guard,
token enforcement, mirror prefix validation, checksum enforcement."""

from __future__ import annotations

import pytest

from backend.app import (
    API_TOKEN,
    _is_loopback_host,
    _safe_restore_target,
    _validate_mirror_prefix,
    app,
)


class TestSafeRestoreTarget:
    def test_valid_names_resolve_under_profiles(self):
        target = _safe_restore_target("profiles/ok.json")
        assert target is not None
        assert "profiles" in str(target)

    def test_dotdot_blocked(self):
        assert _safe_restore_target("profiles/../../x") is None
        assert _safe_restore_target("profiles/sub/../../x") is None
        assert _safe_restore_target("../etc/passwd") is None

    def test_drive_absolute_blocked(self):
        # pathlib join would replace the base entirely for drive-qualified paths.
        assert _safe_restore_target("profiles/C:/evil.txt") is None
        assert _safe_restore_target("profiles/c:\\evil.txt") is None

    def test_root_absolute_blocked(self):
        assert _safe_restore_target("profiles//Windows/System32/evil.txt") is None
        assert _safe_restore_target("profiles//server/share/doc.exe") is None

    def test_unknown_prefix_rejected(self):
        assert _safe_restore_target("evil/ok.json") is None
        assert _safe_restore_target("") is None

    def test_safe_root_names_allowed(self):
        target = _safe_restore_target("settings.json")
        assert target is not None


class TestLoopbackHost:
    @pytest.mark.parametrize(
        "host",
        ["127.0.0.1", "127.0.0.1:8765", "localhost", "localhost:8765", "[::1]", "[::1]:8765", "LOCALHOST:80"],
    )
    def test_loopback_accepted(self, host):
        assert _is_loopback_host(host) is True

    @pytest.mark.parametrize(
        "host",
        ["", "evil.example.com", "evil.example.com:8765", "192.168.1.5", "[fe80::1]", "2130706433"],
    )
    def test_foreign_rejected(self, host):
        assert _is_loopback_host(host) is False


class TestMirrorPrefix:
    def test_https_accepted(self):
        assert _validate_mirror_prefix("https://mirror.example.com/").startswith("https://")

    def test_bare_host_normalized_to_https(self):
        assert _validate_mirror_prefix("mirror.example.com") == "https://mirror.example.com/"

    def test_http_rejected(self):
        with pytest.raises(Exception):
            _validate_mirror_prefix("http://mirror.example.com/")

    def test_credentials_rejected(self):
        with pytest.raises(Exception):
            _validate_mirror_prefix("https://user:pass@mirror.example.com/")

    def test_traversal_rejected(self):
        with pytest.raises(Exception):
            _validate_mirror_prefix("https://mirror.example.com/../evil")


class TestLocalApiGuard:
    def test_docs_disabled(self):
        from fastapi.testclient import TestClient

        with TestClient(app, base_url="http://127.0.0.1") as client:
            assert client.get("/openapi.json").status_code == 404
            assert client.get("/docs").status_code == 404
            assert client.get("/redoc").status_code == 404

    def test_foreign_host_rejected_before_auth(self):
        from fastapi.testclient import TestClient

        with TestClient(app, base_url="http://127.0.0.1") as client:
            resp = client.get("/api/profiles", headers={"Host": "evil.example.com"})
            assert resp.status_code == 421

    def test_cross_origin_rejected(self):
        from fastapi.testclient import TestClient

        with TestClient(app, base_url="http://127.0.0.1") as client:
            resp = client.get(
                "/api/profiles",
                headers={"Origin": "https://evil.example.com", "X-FoxDesk-Token": API_TOKEN},
            )
            assert resp.status_code == 403

    def test_api_requires_token(self):
        from fastapi.testclient import TestClient

        with TestClient(app, base_url="http://127.0.0.1") as client:
            assert client.get("/api/profiles").status_code == 401
            resp = client.get("/api/profiles", headers={"X-FoxDesk-Token": API_TOKEN})
            assert resp.status_code == 200

    def test_ping_and_index_open_on_loopback(self):
        from fastapi.testclient import TestClient

        with TestClient(app, base_url="http://127.0.0.1") as client:
            assert client.get("/api/system/ping").status_code == 200
            assert client.get("/").status_code == 200


class TestChecksumEnforcement:
    def test_update_manager_refuses_missing_checksum(self, tmp_path):
        from backend.update_manager import UpdateManager

        mgr = UpdateManager(
            app_version="1.4.0",
            github_repo="BB0813/foxdesk",
            download_dir=tmp_path,
            user_agent="FoxDesk/test",
            require_checksum=True,
        )
        target = tmp_path / "installer.exe"
        target.write_bytes(b"payload")
        mgr.state.expected_sha256 = None
        with pytest.raises(RuntimeError, match="no SHA256SUMS"):
            mgr._verify_local_file(target)

    def test_app_update_manager_enforces_checksum(self):
        from backend.app import update_manager

        assert update_manager.require_checksum is True


class TestGeoAndBatchEndpoints:
    def test_geo_endpoint_shape(self):
        """Geo endpoint exists, auth-gated, and returns ok=False for a dead proxy."""
        from fastapi.testclient import TestClient

        from backend.app import app

        with TestClient(app, base_url="http://127.0.0.1") as client:
            h = {"X-FoxDesk-Token": API_TOKEN}
            assert client.post("/api/proxy/geo", json={"server": "http://127.0.0.1:9"}).status_code == 401
            r = client.post(
                "/api/proxy/geo",
                json={"server": "http://127.0.0.1:9", "username": "", "password": ""},
                headers=h,
            )
            assert r.status_code == 200
            body = r.json()
            assert body["ok"] is False and body["error"]

    def test_batch_update_endpoint(self):
        from fastapi.testclient import TestClient

        from backend.app import app

        with TestClient(app, base_url="http://127.0.0.1") as client:
            h = {"X-FoxDesk-Token": API_TOKEN}
            # Create then batch-update.
            p = client.post(
                "/api/profiles",
                json={"name": "geo-batch-test", "timezone": "Asia/Taipei"},
                headers=h,
            ).json()
            r = client.post(
                "/api/profiles/batch-update",
                json={"profile_ids": [p["id"]], "timezone": "Europe/Berlin", "locale": "de-DE", "font_pack": "auto"},
                headers=h,
            )
            assert r.status_code == 200
            assert r.json()["updated"] >= 1
            after = client.get("/api/profiles", headers=h).json()
            mine = next(x for x in after if x["id"] == p["id"])
            assert mine["timezone"] == "Europe/Berlin" and mine["locale"] == "de-DE" and mine["font_pack"] == "auto"
            # Invalid font_pack rejected.
            bad = client.post(
                "/api/profiles/batch-update",
                json={"profile_ids": [p["id"]], "font_pack": "nonsense"},
                headers=h,
            )
            assert bad.status_code == 422
            client.delete(f"/api/profiles/{p['id']}", headers=h)


def test_timezone_geo_mismatch_risk(monkeypatch):
    """Profile timezone differing from the proxy's recorded geo flags high risk."""
    from backend.core import Profile
    from backend.profile_logic import environment_risks_for_profile

    class FakePool:
        def get(self, proxy_id):
            if proxy_id == "p1":
                return {"id": "p1", "last_geo": {"ok": True, "timezone": "Europe/Berlin"}}
            raise KeyError(proxy_id)

    from backend import profile_logic

    monkeypatch.setattr(profile_logic, "proxy_pool", FakePool())
    profile = Profile(
        id="x", name="t", created_at="2026-01-01T00:00:00+00:00", updated_at="2026-01-01T00:00:00+00:00",
        engine="chromium", mode="browser", proxy_id="p1", timezone="Asia/Taipei",
    )
    codes = {r["code"]: r["level"] for r in environment_risks_for_profile(profile)}
    assert codes.get("timezone_geo_mismatch") == "high"
