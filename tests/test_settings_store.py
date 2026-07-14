from __future__ import annotations

import json
from pathlib import Path

from backend.settings_store import SettingsStore


def test_settings_defaults_and_clamp(tmp_path: Path) -> None:
    store = SettingsStore(tmp_path / "settings.json")
    view = store.get()
    assert view["update_mirror"] == "ghproxy"
    assert view["max_concurrent_sessions"] == 8
    assert view["idle_session_minutes"] == 0
    assert view["proxy_assign_mode"] == "sticky"
    assert view["proxy_auto_check"] is True

    updated = store.update(
        {
            "max_concurrent_sessions": 100,
            "idle_session_minutes": -5,
            "proxy_assign_mode": "round_robin",
            "proxy_check_interval_sec": 10,
            "proxy_auto_check": False,
            "update_mirror": "official",
        }
    )
    assert updated["max_concurrent_sessions"] == 64
    assert updated["idle_session_minutes"] == 0
    assert updated["proxy_assign_mode"] == "round_robin"
    assert updated["proxy_check_interval_sec"] == 30
    assert updated["proxy_auto_check"] is False
    assert updated["update_mirror"] == "official"


def test_settings_rejects_bad_mirror(tmp_path: Path) -> None:
    store = SettingsStore(tmp_path / "settings.json")
    try:
        store.update({"update_mirror": "evil"})
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_settings_token_not_returned_plaintext(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("FOXDESK_GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    store = SettingsStore(tmp_path / "settings.json")
    store.update({"github_token": "ghp_test_token_value_123456"})
    view = store.get()
    assert view["github_token_set"] is True
    assert "ghp_test" not in json.dumps(view)
    assert view["github_token_source"] in {"stored", "env"}
