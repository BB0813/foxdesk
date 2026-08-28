"""Core singletons: paths, data stores, process registry, activity log.

Import side effects mirror the original backend/app.py: legacy data
migration runs once at import, then the data directories and stores are
created in the same order.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from backend.models import Profile, ProfileIn, ProxyConfig


def _config_home() -> Path:
    if os.name == "nt":
        base = os.environ.get("APPDATA")
        if base:
            return Path(base)
        return Path.home() / "AppData" / "Roaming"
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return Path(base)


def get_app_data_dir() -> Path:
    """Application data directory: %APPDATA%\\FoxDesk (legacy CamoufoxManager still migrated)."""
    home = _config_home()
    modern = home / "FoxDesk"
    legacy = home / "CamoufoxManager"
    # Prefer modern if it already has data; else legacy if only legacy exists.
    if modern.exists() and any(modern.iterdir()):
        return modern
    if legacy.exists() and any(legacy.iterdir()) and not modern.exists():
        return legacy
    return modern


def migrate_legacy_data() -> None:
    """Migrate data from project ./data and CamoufoxManager → FoxDesk."""
    home = _config_home()
    modern = home / "FoxDesk"
    legacy_app = home / "CamoufoxManager"

    # 1) CamoufoxManager → FoxDesk (directory rename/copy once)
    if legacy_app.exists() and not modern.exists():
        try:
            print(f"Migrating app data from {legacy_app} to {modern}")
            shutil.copytree(legacy_app, modern)
            marker = modern / ".migrated_from_camoufoxmanager"
            marker.write_text(str(legacy_app), encoding="utf-8")
        except Exception as exc:
            print(f"Warning: could not migrate CamoufoxManager → FoxDesk: {exc}")

    app_data = get_app_data_dir()
    app_data.mkdir(parents=True, exist_ok=True)

    # 2) Repo-local ./data → app data (older dev layouts)
    legacy_root = Path(__file__).resolve().parent.parent
    legacy_data = legacy_root / "data"
    legacy_profiles = legacy_data / "profiles.json"
    legacy_profiles_dir = legacy_data / "profiles"
    app_profiles = app_data / "profiles.json"
    app_profiles_dir = app_data / "profiles"

    if legacy_profiles.exists() and not app_profiles.exists():
        print(f"Migrating profiles from {legacy_profiles} to {app_profiles}")
        shutil.copy2(legacy_profiles, app_profiles)

    if legacy_profiles_dir.exists() and not app_profiles_dir.exists():
        print(f"Migrating profiles directory from {legacy_profiles_dir} to {app_profiles_dir}")
        shutil.copytree(legacy_profiles_dir, app_profiles_dir)

    # Also pull proxies.json / settings if present in legacy only
    for name in ("proxies.json", "settings.json", "channels.json"):
        src = legacy_app / name if (legacy_app / name).exists() else legacy_data / name
        dst = app_data / name
        if src.exists() and not dst.exists():
            try:
                shutil.copy2(src, dst)
            except OSError:
                pass


APP_VERSION = "1.4.2"
GITHUB_REPO = "BB0813/foxdesk"

if getattr(sys, "frozen", False):
    ROOT = Path(sys._MEIPASS)
    APP_EXECUTABLE = Path(sys.executable)
else:
    ROOT = Path(__file__).resolve().parent.parent
    APP_EXECUTABLE = Path(sys.executable)

STATIC_DIR = ROOT / "static"
WORKER = ROOT / "backend" / "camoufox_worker.py"
WORKER_CHROMIUM = ROOT / "backend" / "chromium_worker.py"
CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0

# Migrate legacy data on startup
migrate_legacy_data()

APP_DATA_DIR = get_app_data_dir()
DATA_DIR = APP_DATA_DIR
RUNTIME_DIR = DATA_DIR / "runtime"
PROFILES_DIR = DATA_DIR / "profiles"

DATA_DIR.mkdir(parents=True, exist_ok=True)
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
PROFILES_DIR.mkdir(parents=True, exist_ok=True)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# profiles.json layout: v1 = bare list (legacy); v2 = wrapped document.
# Legacy files are read transparently and upgraded on the next write.
PROFILE_SCHEMA_VERSION = 2


class ProfileStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.lock = threading.RLock()
        if not self.path.exists():
            self._seed()

    def _seed(self) -> None:
        from backend.storage_util import atomic_write_json

        seed = Profile(
            id=str(uuid.uuid4()),
            name="Default visible profile",
            startup_url="https://browserleaks.com/javascript",
            mode="browser",
            os="auto",
            headless=False,
            persistent_context=True,
            user_data_dir=str((PROFILES_DIR / "default").resolve()),
            humanize=True,
            geoip=False,
            locale="",
            proxy=ProxyConfig(),
            proxy_id="",
            block_images=False,
            block_webrtc=True,
            block_webgl=False,
            disable_coop=True,
            enable_cache=True,
            addons=[],
            extra_args=[],
            tags=[],
            notes="Seed profile. Edit proxy and locale before launch if needed.",
            created_at=now_iso(),
            updated_at=now_iso(),
        )
        atomic_write_json(self.path, {"schema_version": PROFILE_SCHEMA_VERSION, "profiles": [seed.model_dump()]})

    def _read_raw(self) -> list[dict[str, Any]]:
        """Read profile dicts from either layout (bare list or v2 document)."""
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            profiles = data.get("profiles")
            return profiles if isinstance(profiles, list) else []
        return data if isinstance(data, list) else []

    def all(self) -> list[Profile]:
        with self.lock:
            return [Profile(**item) for item in self._read_raw()]

    def save_all(self, profiles: list[Profile]) -> None:
        from backend.storage_util import atomic_write_json

        with self.lock:
            payload = {
                "schema_version": PROFILE_SCHEMA_VERSION,
                "profiles": [profile.model_dump() for profile in profiles],
            }
            atomic_write_json(self.path, payload)

    def get(self, profile_id: str) -> Profile:
        for profile in self.all():
            if profile.id == profile_id:
                return profile
        raise KeyError(profile_id)

    def create(self, incoming: Any) -> Profile:
        from backend.models import ProfileIn

        profiles = self.all()
        profile = Profile(
            **incoming.model_dump(),
            id=str(uuid.uuid4()),
            created_at=now_iso(),
            updated_at=now_iso(),
        )
        profiles.append(profile)
        self.save_all(profiles)
        return profile

    def clone(self, profile_id: str) -> Profile:
        from backend.models import ProfileIn

        original = self.get(profile_id)
        cloned_data = original.model_dump()
        cloned_data.pop("id", None)
        cloned_data.pop("created_at", None)
        cloned_data.pop("updated_at", None)
        cloned_data["name"] = f"{original.name} Copy"
        if cloned_data.get("user_data_dir"):
            cloned_data["user_data_dir"] = f"{cloned_data['user_data_dir']}-copy"
        return self.create(ProfileIn(**cloned_data))

    def update(self, profile_id: str, incoming: Any) -> Profile:
        from backend.models import ProfileIn

        profiles = self.all()
        for idx, profile in enumerate(profiles):
            if profile.id == profile_id:
                updated = Profile(
                    **incoming.model_dump(),
                    id=profile.id,
                    created_at=profile.created_at,
                    updated_at=now_iso(),
                )
                profiles[idx] = updated
                self.save_all(profiles)
                return updated
        raise KeyError(profile_id)

    def delete(self, profile_id: str) -> None:
        profiles = self.all()
        remaining = [profile for profile in profiles if profile.id != profile_id]
        if len(remaining) == len(profiles):
            raise KeyError(profile_id)
        self.save_all(remaining)

    def import_profiles(self, incoming: Any) -> list[Profile]:
        from backend.models import ProfileIn

        imported: list[Profile] = []
        current = [] if incoming.replace else self.all()
        for item in incoming.profiles:
            data = dict(item)
            data.pop("id", None)
            data.pop("created_at", None)
            data.pop("updated_at", None)
            profile = Profile(
                **ProfileIn(**data).model_dump(),
                id=str(uuid.uuid4()),
                created_at=now_iso(),
                updated_at=now_iso(),
            )
            current.append(profile)
            imported.append(profile)
        self.save_all(current)
        return imported


@dataclass
class ManagedProcess:
    id: str
    kind: str
    label: str
    command: list[str]
    process: subprocess.Popen[str]
    started_at: float = field(default_factory=time.time)
    last_activity_at: float = field(default_factory=time.time)
    logs: list[str] = field(default_factory=list)
    timeout: float | None = None
    profile_id: str | None = None
    runtime_id: str | None = None
    runtime_path: str | None = None
    mode: str | None = None
    engine: str | None = None
    last_event: str | None = None
    error_message: str | None = None
    ws_endpoint: str | None = None
    ready: bool = False
    fingerprint_report: dict[str, Any] | None = None

    def status(self) -> str:
        return "running" if self.process.poll() is None else f"exited:{self.process.returncode}"

    def touch(self) -> None:
        self.last_activity_at = time.time()

    def view(self) -> dict[str, Any]:
        code = self.process.returncode
        failed = code not in (None, 0)
        return {
            "id": self.id,
            "kind": self.kind,
            "label": self.label,
            "command": self.command,
            "status": self.status(),
            "pid": self.process.pid,
            "started_at": self.started_at,
            "last_activity_at": self.last_activity_at,
            "idle_seconds": max(0, int(time.time() - self.last_activity_at)),
            "logs": self.logs[-300:],
            "profile_id": self.profile_id,
            "runtime_id": self.runtime_id,
            "mode": self.mode,
            "engine": self.engine or "camoufox",
            "last_event": self.last_event,
            "error_message": self.error_message,
            "ws_endpoint": self.ws_endpoint,
            "ready": self.ready,
            "fingerprint_report": self.fingerprint_report,
            "failed": failed or bool(self.error_message and self.process.poll() is not None),
            "returncode": code,
            "recent_errors": [line for line in self.logs if "error" in line.lower() or line.startswith('{"event": "error"') or '"event":"error"' in line][-8:],
        }


class ProcessRegistry:
    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.items: dict[str, ManagedProcess] = {}
        self._monitor_thread: threading.Thread | None = None
        self._monitor_running = False
        self.idle_session_minutes_provider: Any | None = None

    def add(self, item: ManagedProcess) -> None:
        with self.lock:
            self.items[item.id] = item
        thread = threading.Thread(target=self._capture, args=(item,), daemon=True)
        thread.start()
        self._start_monitor()

    def running_session_count(self) -> int:
        with self.lock:
            return sum(
                1
                for item in self.items.values()
                if item.kind == "session" and item.process.poll() is None
            )

    def _start_monitor(self) -> None:
        with self.lock:
            if self._monitor_thread is not None and self._monitor_thread.is_alive():
                return
            self._monitor_running = True
            self._monitor_thread = threading.Thread(target=self._monitor_timeouts, daemon=True)
            self._monitor_thread.start()

    def _monitor_timeouts(self) -> None:
        from backend.process_utils import stop_popen

        while self._monitor_running:
            time.sleep(1)
            with self.lock:
                items = list(self.items.values())
            idle_minutes = 0
            if self.idle_session_minutes_provider:
                try:
                    idle_minutes = int(self.idle_session_minutes_provider() or 0)
                except Exception:
                    idle_minutes = 0
            idle_seconds = max(0, idle_minutes) * 60
            for item in items:
                if item.timeout and item.kind == "task":
                    if time.time() - item.started_at > item.timeout:
                        if item.process.poll() is None:
                            item.logs.append(f"[TIMEOUT] Process exceeded {item.timeout}s timeout, terminating...")
                            stop_popen(item.process, grace=3)
                            item.logs.append("[TIMEOUT] Process killed")
                if (
                    idle_seconds > 0
                    and item.kind == "session"
                    and item.process.poll() is None
                    and (time.time() - item.last_activity_at) > idle_seconds
                ):
                    item.logs.append(
                        f"[IDLE] Session idle for >{idle_minutes} min, auto-stopping..."
                    )
                    try:
                        stop_popen(item.process, grace=5)
                        item.logs.append("[IDLE] Session stopped")
                    except Exception as exc:
                        item.logs.append(f"[IDLE] stop failed: {exc}")

    # Per-line byte cap for the in-memory log ring: workers already keep
    # bulky payloads out of events, this bounds anything that slips through.
    _MAX_LOG_LINE = 8192

    def _capture(self, item: ManagedProcess) -> None:
        from backend.engine_meta import humanize_chromium_launch_error
        from backend.process_utils import parse_worker_event

        assert item.process.stdout is not None
        for line in item.process.stdout:
            line = line.rstrip()
            if len(line) > self._MAX_LOG_LINE:
                line = line[: self._MAX_LOG_LINE] + f"…(+{len(line) - self._MAX_LOG_LINE} bytes)"
            with self.lock:
                item.logs.append(line)
                if len(item.logs) > 1000:
                    item.logs = item.logs[-1000:]
                event = parse_worker_event(line)
                if not event:
                    # Also scrape bare ws endpoints from non-JSON lines.
                    if "ws://" in line or "wss://" in line:
                        import re

                        m = re.search(r"(wss?://[^\s\"'<>]+)", line, re.I)
                        if m:
                            item.ws_endpoint = m.group(1).rstrip(").,]}\"';")
                            item.touch()
                    continue
                item.last_event = str(event.get("event") or item.last_event)
                item.touch()
                if event.get("event") == "ready":
                    item.ready = True
                    if event.get("ws_endpoint"):
                        item.ws_endpoint = str(event.get("ws_endpoint"))
                    if event.get("mode"):
                        item.mode = str(event.get("mode"))
                if event.get("event") == "error":
                    raw_msg = str(event.get("message") or "worker error")
                    be = event.get("backend") or ""
                    if be:
                        # Chromium workers tag errors with their backend; only
                        # those get chromium-specific install hints.
                        item.error_message = humanize_chromium_launch_error(raw_msg, str(be))
                    else:
                        item.error_message = raw_msg
                    # Keep a short hint line in logs for the UI log pane.
                    try:
                        item.logs.append(f"[error-hint] {item.error_message[:500]}")
                    except Exception:
                        pass
                if event.get("event") in {"endpoint", "ready"} and event.get("ws_endpoint"):
                    item.ws_endpoint = str(event.get("ws_endpoint"))
                if event.get("event") == "fingerprint_report" and isinstance(event.get("report"), dict):
                    item.fingerprint_report = event.get("report")
                if event.get("event") == "navigate":
                    item.touch()
                if event.get("event") == "command_result":
                    item.touch()
                    if event.get("cmd") in {"fingerprint", "fingerprint_probe", "probe"} and isinstance(
                        event.get("report"), dict
                    ):
                        item.fingerprint_report = event.get("report")

    def list(self, kind: str | None = None) -> list[dict[str, Any]]:
        with self.lock:
            values = list(self.items.values())
        if kind:
            values = [item for item in values if item.kind == kind]
        return [item.view() for item in values]

    def get(self, item_id: str) -> ManagedProcess:
        with self.lock:
            if item_id not in self.items:
                raise KeyError(item_id)
            return self.items[item_id]

    def stop(self, item_id: str) -> None:
        from backend.process_utils import stop_popen
        from backend.session_control import send_worker_command

        item = self.get(item_id)
        if item.process.poll() is not None:
            return
        # Ask the worker to close its browser context gracefully first;
        # workers poll the command file ~every 0.4s.
        if item.runtime_path:
            try:
                send_worker_command(Path(item.runtime_path), "stop", timeout=5.0)
            except Exception:
                pass
        item.logs.append("[stop] terminating process tree...")
        stop_popen(item.process, grace=8)
        item.logs.append("[stop] done")
        if item.runtime_path:
            runtime = Path(item.runtime_path)
            for path in (
                runtime,
                runtime.with_suffix(".cmd.jsonl"),
                runtime.with_suffix(".result.jsonl"),
                runtime.with_suffix(".ws"),
            ):
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass


store = ProfileStore(DATA_DIR / "profiles.json")
registry = ProcessRegistry()

from backend.proxy_pool import ProxyPoolStore  # noqa: E402
from backend.settings_store import SettingsStore  # noqa: E402

proxy_pool = ProxyPoolStore(DATA_DIR / "proxies.json")
settings_store = SettingsStore(DATA_DIR / "settings.json")


# --- Channel Store ---
class ChannelStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.lock = threading.RLock()
        if not self.path.exists():
            self._seed()

    def _seed(self) -> None:
        from backend.storage_util import atomic_write_json

        defaults = [
            {"id": "github", "name": "GitHub Official", "prefix": "", "is_default": True},
            {"id": "ghproxy", "name": "GitHub Mirror (China)", "prefix": "https://ghproxy.net/", "is_default": False},
            {"id": "custom", "name": "Custom Mirror", "prefix": "", "is_default": False},
        ]
        atomic_write_json(self.path, defaults)

    def all(self) -> list[dict[str, Any]]:
        with self.lock:
            return json.loads(self.path.read_text(encoding="utf-8"))

    def update(self, channel_id: str, prefix: str) -> None:
        from backend.storage_util import atomic_write_json

        with self.lock:
            channels = json.loads(self.path.read_text(encoding="utf-8"))
            for ch in channels:
                if ch["id"] == channel_id:
                    ch["prefix"] = prefix
                    break
            atomic_write_json(self.path, channels)


channel_store = ChannelStore(DATA_DIR / "channels.json")


class ActivityLog:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.lock = threading.RLock()
        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")

    def log(self, action: str, detail: str = "") -> None:
        from backend.storage_util import atomic_write_json

        with self.lock:
            try:
                entries = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                entries = []
            if not isinstance(entries, list):
                entries = []
            entries.append({
                "time": now_iso(),
                "action": action,
                "detail": detail,
            })
            # Keep last 500 entries
            if len(entries) > 500:
                entries = entries[-500:]
            atomic_write_json(self.path, entries)

    def list(self, limit: int = 100) -> list[dict[str, str]]:
        with self.lock:
            try:
                entries = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                entries = []
            if not isinstance(entries, list):
                entries = []
            return entries[-limit:]


activity = ActivityLog(DATA_DIR / "activity.json")
