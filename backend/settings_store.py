from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any

from backend.storage_util import atomic_write_json, protect_secret, unprotect_secret


DEFAULT_SETTINGS: dict[str, Any] = {
    # official | ghproxy
    "update_mirror": "ghproxy",
    # Optional personal access token for api.github.com (stored encrypted on disk).
    # Prefer env FOXDESK_GITHUB_TOKEN / GITHUB_TOKEN when set.
    "github_token": "",
    "github_token_set": False,
    # Session limits / housekeeping
    "max_concurrent_sessions": 8,
    "idle_session_minutes": 0,  # 0 = disabled
    # Proxy pool
    "proxy_auto_check": True,
    "proxy_check_interval_sec": 300,
    "proxy_assign_mode": "sticky",  # sticky | round_robin | random_healthy
}


class SettingsStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.lock = threading.RLock()
        if not self.path.exists():
            self._write(dict(DEFAULT_SETTINGS))

    def _read_raw(self) -> dict[str, Any]:
        with self.lock:
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                data = {}
            if not isinstance(data, dict):
                data = {}
            merged = dict(DEFAULT_SETTINGS)
            merged.update(data)
            return merged

    def _write(self, data: dict[str, Any]) -> None:
        with self.lock:
            atomic_write_json(self.path, data)

    def get(self) -> dict[str, Any]:
        data = self._read_raw()
        token_plain = unprotect_secret(data.get("github_token") or "")
        env_token = (
            (os.environ.get("FOXDESK_GITHUB_TOKEN") or "").strip()
            or (os.environ.get("GITHUB_TOKEN") or "").strip()
        )
        effective = env_token or token_plain
        mirror = (data.get("update_mirror") or "ghproxy").strip().lower()
        if mirror not in {"official", "ghproxy"}:
            mirror = "ghproxy"
        assign = (data.get("proxy_assign_mode") or "sticky").strip().lower()
        if assign not in {"sticky", "round_robin", "random_healthy"}:
            assign = "sticky"
        try:
            max_sessions = int(data.get("max_concurrent_sessions") or 8)
        except (TypeError, ValueError):
            max_sessions = 8
        max_sessions = max(1, min(64, max_sessions))
        try:
            idle_min = int(data.get("idle_session_minutes") or 0)
        except (TypeError, ValueError):
            idle_min = 0
        idle_min = max(0, min(24 * 60, idle_min))
        try:
            interval = int(data.get("proxy_check_interval_sec") or 300)
        except (TypeError, ValueError):
            interval = 300
        interval = max(30, min(3600, interval))
        return {
            "update_mirror": mirror,
            "github_token_set": bool(effective),
            "github_token_source": (
                "env"
                if env_token
                else ("stored" if token_plain else "none")
            ),
            # Never return the raw token to UI by default.
            "github_token_preview": ("••••" + effective[-4:]) if len(effective) >= 8 else ("set" if effective else ""),
            "max_concurrent_sessions": max_sessions,
            "idle_session_minutes": idle_min,
            "proxy_auto_check": bool(data.get("proxy_auto_check", True)),
            "proxy_check_interval_sec": interval,
            "proxy_assign_mode": assign,
        }

    def get_github_token(self) -> str:
        env_token = (
            (os.environ.get("FOXDESK_GITHUB_TOKEN") or "").strip()
            or (os.environ.get("GITHUB_TOKEN") or "").strip()
        )
        if env_token:
            return env_token
        data = self._read_raw()
        return unprotect_secret(data.get("github_token") or "").strip()

    def get_update_mirror(self) -> str:
        data = self._read_raw()
        mirror = (data.get("update_mirror") or "ghproxy").strip().lower()
        return mirror if mirror in {"official", "ghproxy"} else "ghproxy"

    def update(self, patch: dict[str, Any]) -> dict[str, Any]:
        data = self._read_raw()
        if "update_mirror" in patch and patch["update_mirror"] is not None:
            mirror = str(patch["update_mirror"]).strip().lower()
            if mirror not in {"official", "ghproxy"}:
                raise ValueError("update_mirror must be official or ghproxy")
            data["update_mirror"] = mirror
        if "github_token" in patch:
            token = patch.get("github_token")
            if token is None or str(token).strip() == "":
                data["github_token"] = ""
            else:
                # Allow UI to send sentinel "••••xxxx" without wiping.
                text = str(token).strip()
                if text.startswith("••••") or text == "set":
                    pass
                else:
                    data["github_token"] = protect_secret(text)
        if "clear_github_token" in patch and patch.get("clear_github_token"):
            data["github_token"] = ""
        if "max_concurrent_sessions" in patch and patch["max_concurrent_sessions"] is not None:
            data["max_concurrent_sessions"] = max(1, min(64, int(patch["max_concurrent_sessions"])))
        if "idle_session_minutes" in patch and patch["idle_session_minutes"] is not None:
            data["idle_session_minutes"] = max(0, min(24 * 60, int(patch["idle_session_minutes"])))
        if "proxy_auto_check" in patch and patch["proxy_auto_check"] is not None:
            data["proxy_auto_check"] = bool(patch["proxy_auto_check"])
        if "proxy_check_interval_sec" in patch and patch["proxy_check_interval_sec"] is not None:
            data["proxy_check_interval_sec"] = max(30, min(3600, int(patch["proxy_check_interval_sec"])))
        if "proxy_assign_mode" in patch and patch["proxy_assign_mode"] is not None:
            mode = str(patch["proxy_assign_mode"]).strip().lower()
            if mode not in {"sticky", "round_robin", "random_healthy"}:
                raise ValueError("proxy_assign_mode must be sticky, round_robin, or random_healthy")
            data["proxy_assign_mode"] = mode
        data["github_token_set"] = bool(unprotect_secret(data.get("github_token") or ""))
        self._write(data)
        return self.get()
