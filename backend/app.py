from __future__ import annotations

import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from starlette.middleware.base import BaseHTTPMiddleware


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


APP_VERSION = "1.4.0"
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


class ProxyConfig(BaseModel):
    server: str = ""
    username: str = ""
    password: str = ""

    @field_validator("server")
    @classmethod
    def normalize_server(cls, value: str) -> str:
        value = value.strip()
        if not value:
            return ""
        if "://" not in value:
            value = f"http://{value}"
        allowed = ("http://", "https://", "socks4://", "socks5://")
        if not value.lower().startswith(allowed):
            raise ValueError("proxy server must use http://, https://, socks4://, or socks5://")
        return value


class ProfileIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    startup_url: str = "https://browserleaks.com/javascript"
    mode: Literal["browser", "server"] = "browser"
    # Phase A dual-engine: camoufox (Firefox) | chromium (Playwright Chromium stack)
    engine: Literal["camoufox", "chromium"] = "camoufox"
    # Phase C: chromium automation backend — playwright | patchright | auto
    # auto = prefer patchright when installed, else playwright
    chromium_backend: Literal["auto", "playwright", "patchright"] = "auto"
    # Optional Playwright channel for chromium engine: chrome | msedge | "" (bundled chromium)
    chromium_channel: str = ""
    # Phase B: normal = soft risks only; strict = high risks block launch
    consistency_policy: Literal["normal", "strict"] = "normal"
    os: Literal["auto", "windows", "macos", "linux"] = "auto"
    headless: bool = False
    persistent_context: bool = True
    user_data_dir: str = ""
    humanize: bool = True
    geoip: bool = False
    locale: str = ""
    proxy: ProxyConfig = Field(default_factory=ProxyConfig)
    proxy_id: str = ""
    block_images: bool = False
    block_webrtc: bool = True
    block_webgl: bool = False
    disable_coop: bool = True
    enable_cache: bool = True
    addons: list[str] = Field(default_factory=list)
    extra_args: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    notes: str = ""
    # Fingerprint parameters
    user_agent: str = ""
    navigator_platform: str = ""
    navigator_vendor: str = ""
    screen_width: int = 0
    screen_height: int = 0
    screen_color_depth: int = 0
    device_pixel_ratio: float = 0.0
    hardware_concurrency: int = 0
    device_memory: float = 0.0
    max_touch_points: int = -1  # -1 = leave default; 0+ override
    canvas_noise: bool = True
    webgl_vendor: str = ""
    webgl_renderer: str = ""
    audio_noise: bool = True
    fonts: list[str] = Field(default_factory=list)
    # Phase B: empty/none = no pack; auto = OS pack; windows|macos|linux = fixed pack
    font_pack: str = ""
    timezone: str = ""
    # Client Hints (Chromium; best-effort via init script / context)
    ua_ch_platform: str = ""
    ua_ch_mobile: bool = False
    webrtc_mode: Literal["default", "disable", "public_only", "force_proxy"] = "default"
    media_devices: Literal["default", "random", "empty"] = "default"
    keyboard_layout: str = ""

    @field_validator("startup_url")
    @classmethod
    def validate_startup_url(cls, value: str) -> str:
        value = value.strip()
        if value and not value.startswith(("http://", "https://", "about:")):
            raise ValueError("startup_url must start with http://, https://, or about:")
        return value

    @field_validator("engine", mode="before")
    @classmethod
    def normalize_engine(cls, value: Any) -> str:
        raw = (str(value) if value is not None else "camoufox").strip().lower()
        if raw in {"", "firefox", "camoufox", "default"}:
            return "camoufox"
        if raw in {"chromium", "chrome", "pw", "playwright"}:
            return "chromium"
        raise ValueError("engine must be camoufox or chromium")

    @field_validator("chromium_backend", mode="before")
    @classmethod
    def normalize_chromium_backend(cls, value: Any) -> str:
        raw = (str(value) if value is not None else "auto").strip().lower()
        if raw in {"", "auto", "default"}:
            return "auto"
        if raw in {"playwright", "pw"}:
            return "playwright"
        if raw in {"patchright", "pr", "patched"}:
            return "patchright"
        raise ValueError("chromium_backend must be auto, playwright, or patchright")

    @field_validator("chromium_channel", mode="before")
    @classmethod
    def normalize_chromium_channel(cls, value: Any) -> str:
        raw = (str(value) if value is not None else "").strip().lower()
        if raw in {"", "chromium", "default"}:
            return ""
        if raw in {"chrome", "msedge", "chrome-beta", "msedge-beta", "msedge-dev"}:
            return raw
        raise ValueError("chromium_channel must be empty, chrome, or msedge")

    @field_validator("consistency_policy", mode="before")
    @classmethod
    def normalize_consistency_policy(cls, value: Any) -> str:
        raw = (str(value) if value is not None else "normal").strip().lower()
        if raw in {"", "normal", "default", "soft"}:
            return "normal"
        if raw in {"strict", "hard", "block"}:
            return "strict"
        raise ValueError("consistency_policy must be normal or strict")

    @field_validator("user_agent", mode="before")
    @classmethod
    def normalize_user_agent(cls, value: Any) -> str:
        return (str(value) if value is not None else "").strip()

    @field_validator("font_pack", mode="before")
    @classmethod
    def normalize_font_pack(cls, value: Any) -> str:
        raw = (str(value) if value is not None else "").strip().lower()
        if raw in {"", "none", "off", "manual", "custom"}:
            return ""
        if raw in {"auto", "os", "default_pack"}:
            return "auto"
        if raw in {"windows", "macos", "linux"}:
            return raw
        raise ValueError("font_pack must be empty, auto, windows, macos, or linux")

    @field_validator("addons", "extra_args", "fonts")
    @classmethod
    def normalize_list(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item and str(item).strip()]


class Profile(ProfileIn):
    id: str
    created_at: str
    updated_at: str


class LaunchRequest(BaseModel):
    profile_id: str


class TaskRequest(BaseModel):
    args: list[str] = Field(default_factory=list)


class ImportProfilesRequest(BaseModel):
    profiles: list[dict[str, Any]]
    replace: bool = False


class ProxyTestRequest(BaseModel):
    server: str
    username: str = ""
    password: str = ""


class ChannelUpdateRequest(BaseModel):
    id: str
    prefix: str = ""


class BatchLaunchRequest(BaseModel):
    profile_ids: list[str]


class BatchStopRequest(BaseModel):
    process_ids: list[str]


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
        atomic_write_json(self.path, [seed.model_dump()])

    def all(self) -> list[Profile]:
        with self.lock:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return [Profile(**item) for item in data]

    def save_all(self, profiles: list[Profile]) -> None:
        from backend.storage_util import atomic_write_json

        with self.lock:
            payload = [profile.model_dump() for profile in profiles]
            atomic_write_json(self.path, payload)

    def get(self, profile_id: str) -> Profile:
        for profile in self.all():
            if profile.id == profile_id:
                return profile
        raise KeyError(profile_id)

    def create(self, incoming: ProfileIn) -> Profile:
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
        original = self.get(profile_id)
        cloned_data = original.model_dump()
        cloned_data.pop("id", None)
        cloned_data.pop("created_at", None)
        cloned_data.pop("updated_at", None)
        cloned_data["name"] = f"{original.name} Copy"
        if cloned_data.get("user_data_dir"):
            cloned_data["user_data_dir"] = f"{cloned_data['user_data_dir']}-copy"
        return self.create(ProfileIn(**cloned_data))

    def update(self, profile_id: str, incoming: ProfileIn) -> Profile:
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

    def import_profiles(self, incoming: ImportProfilesRequest) -> list[Profile]:
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

    def _capture(self, item: ManagedProcess) -> None:
        from backend.process_utils import parse_worker_event

        assert item.process.stdout is not None
        for line in item.process.stdout:
            line = line.rstrip()
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
                    item.error_message = humanize_chromium_launch_error(raw_msg, be or None)
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

        item = self.get(item_id)
        if item.process.poll() is not None:
            return
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
app = FastAPI(title="FoxDesk", version=APP_VERSION)

# Localhost API token: blocks casual cross-process abuse on 127.0.0.1.
# Token is generated per process and injected into the UI shell.
API_TOKEN = secrets.token_urlsafe(32)
API_TOKEN_HEADER = "X-FoxDesk-Token"


class LocalApiTokenMiddleware(BaseHTTPMiddleware):
    """Require token for /api/* except a tiny bootstrap endpoint."""

    OPEN_PREFIXES = (
        "/assets/",
        "/favicon",
    )
    OPEN_EXACT = {
        "/",
        "/api/bootstrap",
        "/api/system/ping",
    }

    async def dispatch(self, request: Request, call_next):
        path = request.url.path or "/"
        if path in self.OPEN_EXACT or any(path.startswith(p) for p in self.OPEN_PREFIXES):
            return await call_next(request)
        if path.startswith("/api/"):
            provided = (
                request.headers.get(API_TOKEN_HEADER)
                or request.headers.get("x-foxdesk-token")
                or ""
            )
            if not provided or not secrets.compare_digest(provided, API_TOKEN):
                return JSONResponse(
                    status_code=401,
                    content={
                        "detail": (
                            "unauthorized: missing or invalid X-FoxDesk-Token "
                            "(local API is protected; reload the FoxDesk UI)"
                        )
                    },
                )
        return await call_next(request)


app.add_middleware(LocalApiTokenMiddleware)
app.mount("/assets", StaticFiles(directory=STATIC_DIR), name="assets")

from backend.proxy_health import ProxyHealthScheduler  # noqa: E402
from backend.proxy_pool import ProxyPoolStore  # noqa: E402
from backend.session_control import send_worker_command  # noqa: E402
from backend.settings_store import SettingsStore  # noqa: E402
from backend.setup_manager import SetupManager  # noqa: E402
from backend.templates_data import profile_templates  # noqa: E402
from backend.update_manager import UpdateManager  # noqa: E402

proxy_pool = ProxyPoolStore(DATA_DIR / "proxies.json")
settings_store = SettingsStore(DATA_DIR / "settings.json")
update_manager = UpdateManager(
    app_version=APP_VERSION,
    github_repo=GITHUB_REPO,
    download_dir=DATA_DIR / "updates",
    user_agent=f"FoxDesk/{APP_VERSION}",
    require_checksum=False,  # verify when SHA256SUMS present; CI publishes it for 1.1.0+
    token_provider=settings_store.get_github_token,
    mirror_provider=settings_store.get_update_mirror,
)
registry.idle_session_minutes_provider = lambda: settings_store.get().get("idle_session_minutes", 0)


def _test_proxy_item_for_health(item: dict[str, Any]) -> dict[str, Any]:
    return _test_proxy_connection(
        item.get("server") or "",
        item.get("username") or "",
        item.get("password") or "",
    )


proxy_health = ProxyHealthScheduler(
    list_proxies=proxy_pool.all,
    test_proxy=_test_proxy_item_for_health,
    mark_result=proxy_pool.mark_test_result,
    interval_seconds=float(settings_store.get().get("proxy_check_interval_sec") or 300),
    enabled_provider=lambda: bool(settings_store.get().get("proxy_auto_check", True)),
)
proxy_health.start()

_rr_proxy_index = 0
_rr_proxy_lock = threading.Lock()


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


def camoufox_command(*args: str) -> list[str]:
    """Build a CLI command for camoufox.

    Frozen builds cannot use `FoxDesk.exe -m camoufox`; callers that need
    path/version/fetch should prefer the in-process helpers below.
    """
    executable = shutil.which("camoufox")
    if executable:
        return [executable, *args]
    if getattr(sys, "frozen", False):
        # No valid CLI entry in frozen mode — return a marker command that will fail fast.
        return [str(APP_EXECUTABLE), "--camoufox-cli", *args]
    return [sys.executable, "-m", "camoufox", *args]


def _channel_prefix(channel_id: str) -> str | None:
    for ch in channel_store.all():
        if ch.get("id") == channel_id:
            prefix = (ch.get("prefix") or "").strip()
            return prefix or None
    return None


def run_short(command: list[str], timeout: int = 10) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=timeout,
            creationflags=CREATE_NO_WINDOW,
        )
        return {
            "ok": completed.returncode == 0,
            "returncode": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }
    except Exception as exc:
        return {"ok": False, "returncode": None, "stdout": "", "stderr": str(exc)}


def import_available(module: str) -> bool:
    """Return True only if the module is importable *and* usable.

    For camoufox we also touch fingerprint datapoints so a half-bundled
    install (missing apify zip files) is treated as unavailable.
    """
    def _probe() -> bool:
        __import__(module)
        if module == "camoufox":
            # browserforge -> apify_fingerprint_datapoints data/*.zip
            import apify_fingerprint_datapoints  # noqa: F401
            from camoufox import fingerprints as _fp  # noqa: F401
            from camoufox.pkgman import INSTALL_DIR  # noqa: F401
        return True

    try:
        return _probe()
    except Exception:
        pass
    if getattr(sys, "frozen", False):
        return False
    code = (
        "import camoufox, apify_fingerprint_datapoints\n"
        "from camoufox import fingerprints\n"
        "from camoufox.pkgman import INSTALL_DIR\n"
        if module == "camoufox"
        else f"import {module}\n"
    )
    return subprocess.run(
        [sys.executable, "-c", code],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=CREATE_NO_WINDOW,
    ).returncode == 0


def camoufox_path_info() -> dict[str, Any]:
    """Resolve Camoufox install directory without shelling out."""
    try:
        from camoufox.pkgman import INSTALL_DIR, LAUNCH_FILE, OS_NAME, Version

        if not INSTALL_DIR.exists() or not any(INSTALL_DIR.iterdir()):
            return {
                "ok": False,
                "returncode": 1,
                "stdout": "",
                "stderr": f"not installed ({INSTALL_DIR})",
            }
        launch = INSTALL_DIR / LAUNCH_FILE[OS_NAME]
        if OS_NAME == "mac":
            launch = INSTALL_DIR / "Camoufox.app" / "Contents" / "MacOS" / "camoufox"
        if not Path(launch).exists():
            return {
                "ok": False,
                "returncode": 1,
                "stdout": str(INSTALL_DIR),
                "stderr": f"binary missing: {launch}",
            }
        try:
            Version.from_path(INSTALL_DIR)
        except Exception as exc:
            return {
                "ok": False,
                "returncode": 1,
                "stdout": str(INSTALL_DIR),
                "stderr": str(exc),
            }
        return {
            "ok": True,
            "returncode": 0,
            "stdout": str(INSTALL_DIR),
            "stderr": "",
        }
    except Exception as exc:
        if getattr(sys, "frozen", False):
            return {"ok": False, "returncode": 1, "stdout": "", "stderr": str(exc)}
        return run_short(camoufox_command("path"), timeout=8)


def camoufox_version_info() -> dict[str, Any]:
    """Resolve Camoufox package + binary version without shelling out."""
    lines: list[str] = []
    try:
        from importlib.metadata import PackageNotFoundError, version as pkg_version

        try:
            lines.append(f"Pip package:\tv{pkg_version('camoufox')}")
        except PackageNotFoundError:
            # Frozen builds often lack dist-info; import success is enough.
            if import_available("camoufox"):
                lines.append("Pip package:\tbundled")
            else:
                lines.append("Pip package:\tNot installed!")
    except Exception as exc:
        lines.append(f"Pip package:\t{exc}")
    try:
        from camoufox.pkgman import installed_verstr

        lines.append(f"Camoufox:\tv{installed_verstr()}")
        return {"ok": True, "returncode": 0, "stdout": "\n".join(lines), "stderr": ""}
    except Exception as exc:
        lines.append(f"Camoufox:\tNot downloaded! ({exc})")
        if getattr(sys, "frozen", False):
            return {"ok": False, "returncode": 1, "stdout": "\n".join(lines), "stderr": str(exc)}
        cli = run_short(camoufox_command("version"), timeout=8)
        if cli.get("stdout") or cli.get("stderr"):
            return cli
        return {"ok": False, "returncode": 1, "stdout": "\n".join(lines), "stderr": str(exc)}


setup_manager = SetupManager(
    is_frozen=bool(getattr(sys, "frozen", False)),
    executable=APP_EXECUTABLE,
    root=ROOT if not getattr(sys, "frozen", False) else Path(sys.executable).resolve().parent,
    create_no_window=CREATE_NO_WINDOW,
    camoufox_command=camoufox_command,
    import_available=import_available,
    channel_prefix=_channel_prefix,
    marker_path=DATA_DIR / "setup.completed",
)


def normalize_engine_name(value: str | None) -> str:
    raw = (value or "camoufox").strip().lower()
    if raw in {"", "firefox", "camoufox", "default"}:
        return "camoufox"
    if raw in {"chromium", "chrome", "pw", "playwright"}:
        return "chromium"
    return "camoufox"


def normalize_chromium_backend_name(value: str | None) -> str:
    raw = (value or "auto").strip().lower()
    if raw in {"", "auto", "default"}:
        return "auto"
    if raw in {"playwright", "pw"}:
        return "playwright"
    if raw in {"patchright", "pr", "patched"}:
        return "patchright"
    return "auto"


def chromium_backend_available(name: str) -> bool:
    name = normalize_chromium_backend_name(name)
    if name == "auto":
        return import_available("playwright") or import_available("patchright")
    if name == "patchright":
        return import_available("patchright")
    return import_available("playwright")


def chromium_install_hint(backend: str | None = None) -> str:
    """User-facing install commands for Chromium stack gaps."""
    name = normalize_chromium_backend_name(backend)
    if name == "patchright":
        return "pip install patchright && patchright install chromium"
    if name == "playwright":
        return "pip install playwright && playwright install chromium"
    # auto / both
    return (
        "pip install playwright patchright && "
        "playwright install chromium && patchright install chromium"
    )


def humanize_chromium_launch_error(exc: BaseException | str, backend: str | None = None) -> str:
    """Map Playwright/Patchright launch failures to actionable install text."""
    text = str(exc)
    low = text.lower()
    be = normalize_chromium_backend_name(backend) if backend else "auto"
    hint_pr = "patchright install chromium"
    hint_pw = "playwright install chromium"
    hint = hint_pr if be == "patchright" else (hint_pw if be == "playwright" else f"{hint_pw}  (or {hint_pr})")
    if any(
        key in low
        for key in (
            "executable doesn't exist",
            "browser not found",
            "browsers are not installed",
            "please run the following command to download",
            "chromium distribution is not found",
            "browserType.launch",
            "browser_type.launch",
        )
    ) or ("chromium" in low and "install" in low):
        return (
            f"Chromium browser binary missing for backend={be}. "
            f"Run: {hint}. "
            f"Full stack: {chromium_install_hint(be)}. "
            f"Detail: {text}"
        )
    if "channel" in low and "chrome" in low:
        return (
            "chromium_channel=chrome failed — install Google Chrome or clear channel to use bundled Chromium. "
            f"Detail: {text}"
        )
    if "patchright" in low and "not installed" in low:
        return f"patchright package missing. Run: {chromium_install_hint('patchright')}. Detail: {text}"
    if "playwright" in low and "not installed" in low:
        return f"playwright package missing. Run: {chromium_install_hint('playwright')}. Detail: {text}"
    return text


def resolve_chromium_backend(value: str | None) -> str:
    """Resolve auto → patchright if installed, else playwright."""
    name = normalize_chromium_backend_name(value)
    if name == "patchright":
        if import_available("patchright"):
            return "patchright"
        raise RuntimeError(
            f"chromium_backend=patchright but patchright is not installed. "
            f"Run: {chromium_install_hint('patchright')}"
        )
    if name == "playwright":
        if import_available("playwright"):
            return "playwright"
        raise RuntimeError(
            f"chromium_backend=playwright but playwright is not installed. "
            f"Run: {chromium_install_hint('playwright')}"
        )
    # auto
    if import_available("patchright"):
        return "patchright"
    if import_available("playwright"):
        return "playwright"
    raise RuntimeError(
        f"neither patchright nor playwright is installed. Run: {chromium_install_hint('auto')}"
    )


def worker_command(runtime_path: Path, engine: str = "camoufox") -> list[str]:
    """Build a command that works in source and frozen (PyInstaller) modes."""
    eng = normalize_engine_name(engine)
    if getattr(sys, "frozen", False):
        # Frozen binary dispatches on runtime JSON engine field inside --worker.
        return [str(APP_EXECUTABLE), "--worker", str(runtime_path)]
    script = WORKER_CHROMIUM if eng == "chromium" else WORKER
    return [sys.executable, str(script), str(runtime_path)]


def start_process(
    kind: str,
    label: str,
    command: list[str],
    timeout: float | None = None,
    *,
    profile_id: str | None = None,
    runtime_id: str | None = None,
    runtime_path: str | None = None,
    mode: str | None = None,
    engine: str | None = None,
) -> ManagedProcess:
    item_id = str(uuid.uuid4())
    # On POSIX start a new session so we can signal the process group.
    kwargs: dict[str, Any] = {
        "args": command,
        "cwd": ROOT,
        "text": True,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.STDOUT,
        "bufsize": 1,
        "creationflags": CREATE_NO_WINDOW,
    }
    if os.name != "nt":
        kwargs["start_new_session"] = True
    # Chromium may resolve browsers under FoxDesk data dir.
    env = os.environ.copy()
    browsers = DATA_DIR / "browsers"
    if browsers.exists():
        env.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(browsers))
        env.setdefault("FOXDESK_BROWSERS_PATH", str(browsers))
    kwargs["env"] = env
    process = subprocess.Popen(**kwargs)
    item = ManagedProcess(
        id=item_id,
        kind=kind,
        label=label,
        command=command,
        process=process,
        timeout=timeout,
        profile_id=profile_id,
        runtime_id=runtime_id,
        runtime_path=runtime_path,
        mode=mode,
        engine=normalize_engine_name(engine),
    )
    registry.add(item)
    return item


def cleanup_runtime_files(max_age_hours: float = 24.0, keep_active: bool = True) -> dict[str, int]:
    cutoff = time.time() - max_age_hours * 3600
    active_paths: set[str] = set()
    if keep_active:
        for item in registry.list("session"):
            # view doesn't include runtime_path; inspect registry items
            pass
    with registry.lock:
        for item in registry.items.values():
            if item.runtime_path and item.process.poll() is None:
                active_paths.add(str(Path(item.runtime_path).resolve()))
    removed = 0
    kept = 0
    for path in RUNTIME_DIR.glob("*.json"):
        try:
            resolved = str(path.resolve())
            if resolved in active_paths:
                kept += 1
                continue
            if path.stat().st_mtime < cutoff or not keep_active:
                path.unlink(missing_ok=True)
                removed += 1
            else:
                # also remove orphaned finished runtimes older than 1h even if under max_age
                if path.stat().st_mtime < time.time() - 3600:
                    path.unlink(missing_ok=True)
                    removed += 1
                else:
                    kept += 1
        except OSError:
            continue
    return {"removed": removed, "kept": kept}


def pick_proxy_from_pool(profile: Profile) -> dict[str, Any] | None:
    """Resolve proxy according to settings: sticky | round_robin | random_healthy."""
    mode = (settings_store.get().get("proxy_assign_mode") or "sticky").strip().lower()
    items = proxy_pool.all()
    if not items:
        return None

    # Explicit binding always wins for sticky; for other modes still prefer healthy pool.
    if mode == "sticky":
        proxy_id = (profile.proxy_id or "").strip()
        if proxy_id:
            try:
                return proxy_pool.get(proxy_id)
            except KeyError:
                return None
        return None

    healthy = [p for p in items if p.get("last_ok") is True]
    candidates = healthy or items
    if mode == "random_healthy":
        import random

        return random.choice(candidates)
    if mode == "round_robin":
        global _rr_proxy_index
        with _rr_proxy_lock:
            item = candidates[_rr_proxy_index % len(candidates)]
            _rr_proxy_index += 1
            return item
    return None


def apply_proxy_pool_to_profile(profile: Profile) -> Profile:
    item = pick_proxy_from_pool(profile)
    if not item:
        # sticky with no proxy_id: keep manual proxy on profile
        return profile
    data = profile.model_dump()
    data["proxy"] = {
        "server": item.get("server") or "",
        "username": item.get("username") or "",
        "password": item.get("password") or "",
    }
    data["proxy_id"] = item.get("id") or data.get("proxy_id") or ""
    return Profile(**data)


@app.get("/")
def index() -> HTMLResponse:
    """Serve UI shell with per-process API token injected."""
    html_path = STATIC_DIR / "index.html"
    html = html_path.read_text(encoding="utf-8")
    bootstrap = (
        "<script>"
        f"window.__FOXDESK_BOOT__={json.dumps({'token': API_TOKEN, 'version': APP_VERSION})};"
        "</script>"
    )
    if "</head>" in html:
        html = html.replace("</head>", bootstrap + "\n  </head>", 1)
    else:
        html = bootstrap + html
    return HTMLResponse(content=html)


@app.get("/api/bootstrap")
def api_bootstrap() -> dict[str, Any]:
    """Public bootstrap metadata for UI clients."""
    return {
        "ok": True,
        "app_name": "FoxDesk",
        "app_version": APP_VERSION,
        "token_header": API_TOKEN_HEADER,
        "auth_required": True,
        "note": "Use the token injected into index.html (window.__FOXDESK_BOOT__).",
    }


@app.get("/api/system/ping")
def system_ping() -> dict[str, Any]:
    return {"ok": True, "app_version": APP_VERSION}


@app.get("/api/system")
def system() -> dict[str, Any]:
    installed = import_available("camoufox")
    version = camoufox_version_info() if installed else {
        "ok": False,
        "returncode": 1,
        "stdout": "",
        "stderr": "camoufox not installed",
    }
    path = camoufox_path_info() if installed else {
        "ok": False,
        "returncode": 1,
        "stdout": "",
        "stderr": "camoufox not installed",
    }
    path_ok = bool(path and path.get("ok") and (path.get("stdout") or "").strip())
    sessions = registry.list("session")
    running_sessions = sum(1 for s in sessions if s.get("status") == "running")
    install_flow = [
        {
            "task": "install",
            "label": "Install Python package",
            "done": installed,
            "command": (
                ["bundled"]
                if getattr(sys, "frozen", False)
                else [sys.executable, "-m", "pip", "install", "camoufox"]
            ),
        },
        {
            "task": "fetch",
            "label": "Fetch browser binary",
            "done": path_ok,
            "command": camoufox_command("fetch"),
        },
        {
            "task": "health",
            "label": "Lightweight health check",
            "done": path_ok,
            "command": ["foxdesk", "health"],
        },
    ]
    first_run = (not installed) or (not path_ok)
    setup = setup_manager.status()
    settings_view = settings_store.get()
    chrome = detect_google_chrome_install()
    return {
        "app_name": "FoxDesk",
        "app_version": APP_VERSION,
        "python": sys.version.split()[0],
        "executable": sys.executable,
        "frozen": bool(getattr(sys, "frozen", False)),
        "data_dir": str(DATA_DIR),
        "camoufox_installed": installed,
        "camoufox_version": version,
        "camoufox_path": path,
        "playwright_installed": import_available("playwright"),
        "patchright_installed": import_available("patchright"),
        "google_chrome": chrome,
        "chromium_stack": {
            "playwright": import_available("playwright"),
            "patchright": import_available("patchright"),
            "default_backend": (
                "patchright"
                if import_available("patchright")
                else ("playwright" if import_available("playwright") else None)
            ),
            "hint": (
                chromium_install_hint("auto")
                if not (
                    import_available("patchright") or import_available("playwright")
                )
                else (
                    chromium_install_hint("patchright")
                    if not import_available("patchright")
                    else (
                        chromium_install_hint("playwright")
                        if not import_available("playwright")
                        else "patchright + playwright ready (auto prefers patchright)"
                    )
                )
            ),
        },
        "install_flow": install_flow,
        "running_sessions": running_sessions,
        "first_run": first_run,
        "needs_setup": first_run or bool(setup.get("needs_setup")),
        "setup": setup,
        "github_repo": GITHUB_REPO,
        "api_auth": True,
        "api_token_header": API_TOKEN_HEADER,
        "proxy_pool_count": len(proxy_pool.all()),
        "profile_count": len(store.all()),
        "settings": settings_view,
        "update_mirror": settings_view.get("update_mirror"),
        "github_token_set": settings_view.get("github_token_set"),
    }


class SetupStartRequest(BaseModel):
    channel: str = "github"
    auto: bool = True
    force: bool = False


@app.get("/api/setup/status")
def setup_status() -> dict[str, Any]:
    return setup_manager.status()


@app.post("/api/setup/start")
def setup_start(request: SetupStartRequest | None = None) -> dict[str, Any]:
    req = request or SetupStartRequest()
    # Persist custom channel prefix if provided via channel store already.
    result = setup_manager.start(channel=req.channel or "github", auto=req.auto, force=req.force)
    activity.log("setup_start", f"channel={req.channel} force={req.force}")
    return result


@app.post("/api/setup/complete")
def setup_complete() -> dict[str, Any]:
    """Mark guided setup as completed even if user skips (not recommended)."""
    setup_manager.mark_completed()
    return {"ok": True, **setup_manager.status()}


class SettingsUpdateRequest(BaseModel):
    update_mirror: str | None = None
    github_token: str | None = None
    clear_github_token: bool = False
    max_concurrent_sessions: int | None = None
    idle_session_minutes: int | None = None
    proxy_auto_check: bool | None = None
    proxy_check_interval_sec: int | None = None
    proxy_assign_mode: str | None = None


@app.get("/api/settings")
def get_settings() -> dict[str, Any]:
    view = settings_store.get()
    return {
        "ok": True,
        **view,
        "proxy_health": proxy_health.status(),
        "running_sessions": registry.running_session_count(),
    }


@app.put("/api/settings")
def put_settings(request: SettingsUpdateRequest) -> dict[str, Any]:
    try:
        view = settings_store.update(request.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    # Refresh update manager effective config immediately.
    update_manager.configure(
        github_token=settings_store.get_github_token(),
        mirror=settings_store.get_update_mirror(),
    )
    proxy_health.configure(interval_seconds=float(view.get("proxy_check_interval_sec") or 300))
    activity.log(
        "settings_update",
        f"mirror={view.get('update_mirror')} token={view.get('github_token_source')} "
        f"max_sessions={view.get('max_concurrent_sessions')} proxy_mode={view.get('proxy_assign_mode')}",
    )
    return {"ok": True, **view, "proxy_health": proxy_health.status()}


@app.post("/api/system/diagnostics")
def export_diagnostics() -> dict[str, Any]:
    """Write a redacted diagnostics bundle under data_dir/logs (no secrets/cookies)."""
    from backend.storage_util import atomic_write_json

    logs_dir = DATA_DIR / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = logs_dir / f"diagnostics-{stamp}.json"

    settings_view = settings_store.get()
    try:
        update_status = update_manager.status()
    except Exception as exc:
        update_status = {"error": str(exc)}

    # Redact sensitive fields from update logs / asset URLs already public.
    safe_update = {
        k: update_status.get(k)
        for k in (
            "status",
            "current",
            "latest",
            "release_name",
            "release_url",
            "prerelease",
            "asset_name",
            "progress",
            "error",
            "checked_at",
            "mirror",
            "github_token_set",
            "sha256_verified",
            "logs",
        )
        if isinstance(update_status, dict)
    }

    chrome = detect_google_chrome_install()
    payload = {
        "generated_at": now_iso(),
        "app_name": "FoxDesk",
        "app_version": APP_VERSION,
        "python": sys.version,
        "executable": sys.executable,
        "frozen": bool(getattr(sys, "frozen", False)),
        "platform": sys.platform,
        "data_dir": str(DATA_DIR),
        "github_repo": GITHUB_REPO,
        "settings": settings_view,
        "setup": setup_manager.status(),
        "profile_count": len(store.all()),
        "proxy_count": len(proxy_pool.all()),
        "running_sessions": sum(1 for s in registry.list("session") if s.get("status") == "running"),
        "update": safe_update,
        "camoufox_installed": import_available("camoufox"),
        "playwright_installed": import_available("playwright"),
        "patchright_installed": import_available("patchright"),
        "google_chrome": {"installed": chrome.get("installed"), "path_count": len(chrome.get("paths") or [])},
        "engines_summary": {
            p.id: {
                "name": p.name,
                "engine": normalize_engine_name(getattr(p, "engine", None)),
                "chromium_backend": getattr(p, "chromium_backend", None),
                "chromium_channel": getattr(p, "chromium_channel", None) or "",
                "headless": p.headless,
                "tags": list(p.tags or [])[:12],
            }
            for p in store.all()[:80]
        },
        "note": "Redacted: no proxy passwords, cookies, or API tokens included. No anti-detect guarantee.",
    }
    atomic_write_json(out_path, payload)
    activity.log("diagnostics_export", str(out_path))
    return {"ok": True, "path": str(out_path)}


@app.post("/api/system/health")
def system_health() -> dict[str, Any]:
    """Lightweight Camoufox health check (no full self-test hang)."""
    started = time.time()
    installed = import_available("camoufox")
    if not installed:
        return {
            "ok": False,
            "checks": {"import": False, "path": False},
            "error": "camoufox package not installed",
            "latency_ms": int((time.time() - started) * 1000),
        }
    path = camoufox_path_info()
    path_text = (path.get("stdout") or "").strip()
    path_exists = bool(path.get("ok") and path_text and Path(path_text).exists())
    version = camoufox_version_info()
    ok = path_exists and bool(version.get("ok") or version.get("stdout"))
    return {
        "ok": ok,
        "checks": {
            "import": True,
            "path": path_exists,
            "path_value": path_text,
            "version": version.get("stdout") or version.get("stderr") or "",
        },
        "error": None if ok else "browser binary missing; run setup/fetch",
        "latency_ms": int((time.time() - started) * 1000),
    }


@app.post("/api/system/cleanup-runtime")
def system_cleanup_runtime(max_age_hours: float = 24.0) -> dict[str, Any]:
    result = cleanup_runtime_files(max_age_hours=max_age_hours)
    activity.log("runtime_cleanup", f"removed={result['removed']} kept={result['kept']}")
    return {"ok": True, **result}


class UpdateCheckRequest(BaseModel):
    include_prerelease: bool | None = None
    force: bool = False


class UpdateInstallRequest(BaseModel):
    exit_after: bool = True


@app.get("/api/system/updates")
def system_updates() -> dict[str, Any]:
    """Check GitHub Releases for a newer version (includes prereleases when current is beta)."""
    result = update_manager.check()
    return {
        "ok": result.get("status") != "failed",
        **result,
        "name": result.get("release_name"),
    }


@app.post("/api/system/updates/check")
def system_updates_check(request: UpdateCheckRequest | None = None) -> dict[str, Any]:
    req = request or UpdateCheckRequest()
    result = update_manager.check(
        include_prerelease=req.include_prerelease,
        force=bool(req.force),
    )
    activity.log("update_check", f"latest={result.get('latest')} status={result.get('status')}")
    return {"ok": result.get("status") != "failed", **result, "name": result.get("release_name")}


@app.get("/api/system/updates/status")
def system_updates_status() -> dict[str, Any]:
    return update_manager.status()


@app.post("/api/system/updates/download")
def system_updates_download() -> dict[str, Any]:
    result = update_manager.start_download()
    activity.log("update_download", f"status={result.get('status')} asset={result.get('asset_name')}")
    return {"ok": result.get("status") not in {"failed"}, **result}


@app.post("/api/system/updates/install")
def system_updates_install(request: UpdateInstallRequest | None = None) -> dict[str, Any]:
    req = request or UpdateInstallRequest()
    result = update_manager.install(exit_after=req.exit_after)
    activity.log("update_install", f"ok={result.get('ok')} path={result.get('local_path')}")
    if not result.get("ok"):
        raise HTTPException(status_code=409, detail=result.get("error") or "install failed")
    return result


@app.post("/api/tasks/{name}")
def start_task(name: str, request: TaskRequest | None = None) -> dict[str, Any]:
    allowed = {"install", "fetch", "test", "remove", "version", "path"}
    if name not in allowed:
        raise HTTPException(status_code=404, detail="unknown task")
    args = request.args if request else []

    # Frozen builds cannot run `python -m camoufox` against FoxDesk.exe.
    # Use in-process helpers / guided setup instead of a broken subprocess.
    if getattr(sys, "frozen", False) and name in {"install", "fetch", "version", "path", "remove"}:
        if name == "install":
            ok = import_available("camoufox")
            return {
                "id": f"inline-{int(time.time() * 1000)}",
                "kind": "task",
                "label": "install (bundled)",
                "status": "exited" if ok else "failed",
                "returncode": 0 if ok else 1,
                "logs": ["camoufox bundled" if ok else "camoufox missing from application bundle"],
                "ok": ok,
            }
        if name in {"path", "version"}:
            info = camoufox_path_info() if name == "path" else camoufox_version_info()
            text = (info.get("stdout") or info.get("stderr") or "").strip()
            return {
                "id": f"inline-{int(time.time() * 1000)}",
                "kind": "task",
                "label": f"camoufox {name}",
                "status": "exited" if info.get("ok") else "failed",
                "returncode": 0 if info.get("ok") else 1,
                "logs": text.splitlines() or [info.get("stderr") or ""],
                "ok": bool(info.get("ok")),
            }
        if name == "fetch":
            result = setup_manager.start(channel="github", auto=True, force=True)
            return {
                "id": f"setup-{int(time.time() * 1000)}",
                "kind": "task",
                "label": "camoufox fetch (guided)",
                "status": "running" if result.get("status") == "running" else result.get("status"),
                "returncode": None,
                "logs": result.get("logs") or ["started guided setup fetch"],
                "ok": result.get("status") != "failed",
                "setup": result,
            }
        if name == "remove":
            try:
                from camoufox.pkgman import CamoufoxFetcher

                removed = CamoufoxFetcher.cleanup()
                return {
                    "id": f"inline-{int(time.time() * 1000)}",
                    "kind": "task",
                    "label": "camoufox remove",
                    "status": "exited",
                    "returncode": 0,
                    "logs": ["removed" if removed else "nothing to remove"],
                    "ok": True,
                }
            except Exception as exc:
                raise HTTPException(status_code=500, detail=str(exc)) from exc

    if name == "install":
        command = [sys.executable, "-m", "pip", "install", "camoufox", *args]
        label = "pip install camoufox"
        timeout = 120.0  # pip install can take a while
    elif name == "fetch":
        command = camoufox_command(name, *args)
        label = f"camoufox {name}"
        timeout = 180.0  # fetch can take a long time
    elif name == "test":
        command = camoufox_command(name, *args)
        label = f"camoufox {name}"
        timeout = 60.0  # test task timeout
    else:
        command = camoufox_command(name, *args)
        label = f"camoufox {name}"
        timeout = 30.0  # other tasks
    item = start_process("task", label, command, timeout=timeout)
    return item.view()


@app.get("/api/tasks")
def list_tasks() -> list[dict[str, Any]]:
    return registry.list("task")


@app.get("/api/profiles")
def list_profiles() -> list[Profile]:
    return store.all()


@app.post("/api/profiles")
def create_profile(profile: ProfileIn) -> Profile:
    data = profile.model_dump()
    engine = normalize_engine_name(data.get("engine"))
    data["engine"] = engine
    if data.get("user_data_dir"):
        data["user_data_dir"] = str(resolve_user_data_dir(data["user_data_dir"]))
    elif data.get("name"):
        slug = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in data["name"]).strip("-") or "profile"
        if engine == "chromium" and not slug.endswith("-chromium"):
            slug = f"{slug}-chromium"
        data["user_data_dir"] = str(PROFILES_DIR / slug)
    created = store.create(ProfileIn(**data))
    activity.log("profile_create", f"{created.name} engine={engine}")
    return created


@app.get("/api/profiles/export")
def export_profiles() -> JSONResponse:
    return JSONResponse(
        {
            "exported_at": now_iso(),
            "schema": "camoufox-manager.profiles.v1",
            "profiles": [profile.model_dump() for profile in store.all()],
        }
    )


@app.post("/api/profiles/import")
def import_profiles(request: ImportProfilesRequest) -> list[Profile]:
    try:
        return store.import_profiles(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


@app.post("/api/profiles/{profile_id}/clone")
def clone_profile(profile_id: str) -> Profile:
    try:
        return store.clone(profile_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="profile not found") from None


@app.put("/api/profiles/{profile_id}")
def update_profile(profile_id: str, profile: ProfileIn) -> Profile:
    try:
        data = profile.model_dump()
        if data.get("user_data_dir"):
            data["user_data_dir"] = str(resolve_user_data_dir(data["user_data_dir"]))
        updated = store.update(profile_id, ProfileIn(**data))
        activity.log("profile_update", updated.name)
        return updated
    except KeyError:
        raise HTTPException(status_code=404, detail="profile not found") from None


@app.delete("/api/profiles/{profile_id}")
def delete_profile(profile_id: str) -> dict[str, bool]:
    try:
        store.delete(profile_id)
        activity.log("profile_delete", profile_id)
        return {"ok": True}
    except KeyError:
        raise HTTPException(status_code=404, detail="profile not found") from None


@app.post("/api/profiles/{profile_id}/open-data-dir")
def open_profile_data_dir(profile_id: str) -> dict[str, Any]:
    try:
        profile = store.get(profile_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="profile not found") from None
    if not profile.user_data_dir:
        raise HTTPException(status_code=409, detail="profile has no user_data_dir")

    target = Path(profile.user_data_dir).expanduser()
    target.mkdir(parents=True, exist_ok=True)
    try:
        if os.name == "nt":
            os.startfile(str(target))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(target)])
        else:
            subprocess.Popen(["xdg-open", str(target)])
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from None
    return {"ok": True, "path": str(target)}


@app.post("/api/sessions")
def launch_session(request: LaunchRequest) -> dict[str, Any]:
    settings_view = settings_store.get()
    max_sessions = int(settings_view.get("max_concurrent_sessions") or 8)
    running = registry.running_session_count()
    if running >= max_sessions:
        raise HTTPException(
            status_code=429,
            detail=f"max concurrent sessions reached ({running}/{max_sessions}). Stop some sessions or raise the limit in settings.",
        )
    try:
        profile = store.get(request.profile_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="profile not found") from None

    profile = apply_proxy_pool_to_profile(profile)
    profile = normalize_profile_paths(profile)
    engine = normalize_engine_name(getattr(profile, "engine", None))

    if engine == "camoufox" and not import_available("camoufox"):
        raise HTTPException(status_code=409, detail="camoufox is not installed. Run fetch/install first.")
    resolved_backend = None
    if engine == "chromium":
        try:
            resolved_backend = resolve_chromium_backend(getattr(profile, "chromium_backend", None))
        except Exception as exc:
            raise HTTPException(
                status_code=409,
                detail=humanize_chromium_launch_error(exc, getattr(profile, "chromium_backend", None)),
            ) from None

    # Pre-launch validation
    errors = validate_profile_for_launch(profile)
    if errors:
        raise HTTPException(status_code=400, detail="; ".join(errors))

    if profile.persistent_context and profile.user_data_dir:
        Path(profile.user_data_dir).expanduser().mkdir(parents=True, exist_ok=True)

    cleanup_runtime_files(max_age_hours=24.0)
    runtime_id = str(uuid.uuid4())
    runtime_path = RUNTIME_DIR / f"{runtime_id}.json"
    payload = profile.model_dump()
    payload["engine"] = engine
    if resolved_backend:
        payload["chromium_backend"] = resolved_backend
    payload["_runtime_id"] = runtime_id
    payload["_profile_id"] = profile.id
    # Auto probe fingerprint once after browser ready when requested via tags/notes.
    tags = {str(t).lower() for t in (profile.tags or [])}
    if "probe" in tags or "fingerprint" in tags:
        payload["_auto_fingerprint_probe"] = True
    from backend.storage_util import atomic_write_json

    atomic_write_json(runtime_path, payload)
    # Ensure command/result sidecars exist.
    runtime_path.with_suffix(".cmd.jsonl").write_text("", encoding="utf-8")
    runtime_path.with_suffix(".result.jsonl").write_text("", encoding="utf-8")
    command = worker_command(runtime_path, engine=engine)
    item = start_process(
        "session",
        profile.name,
        command,
        profile_id=profile.id,
        runtime_id=runtime_id,
        runtime_path=str(runtime_path),
        mode=profile.mode,
        engine=engine,
    )
    with registry.lock:
        item.logs.append(f"[runtime] {runtime_path.name}")
        item.logs.append(f"[engine] {engine}")
        if resolved_backend:
            item.logs.append(f"[chromium_backend] {resolved_backend}")
            if not import_available("patchright") and resolved_backend == "playwright":
                item.logs.append(
                    "[hint] patchright not installed — webdriver more likely. "
                    f"Install: {chromium_install_hint('patchright')}"
                )
        channel = (getattr(profile, "chromium_channel", None) or "").strip()
        if channel:
            item.logs.append(f"[chromium_channel] {channel}")
        if profile.proxy and profile.proxy.server:
            item.logs.append(f"[proxy] {profile.proxy.server}")
        tags = {str(t).lower() for t in (profile.tags or [])}
        if tags & {"ai", "chatgpt", "claude", "gemini"}:
            item.logs.append(
                "[ai] own-account official flows only — no signup/subscribe guarantee; "
                "align proxy with timezone/locale; prefer headed + persistent"
            )
    backend_note = f" backend={resolved_backend}" if resolved_backend else ""
    activity.log("session_launch", f"{profile.name} engine={engine}{backend_note} (pid {item.process.pid})")
    view = item.view()
    view["runtime_id"] = runtime_id
    view["profile_id"] = profile.id
    view["engine"] = engine
    if resolved_backend:
        view["chromium_backend"] = resolved_backend
    view["running_sessions"] = registry.running_session_count()
    view["max_concurrent_sessions"] = max_sessions
    risks = environment_risks_for_profile(profile)
    view["environment_risks"] = risks
    high = sum(1 for r in risks if r.get("level") == "high")
    medium = sum(1 for r in risks if r.get("level") == "medium")
    if high or medium:
        with registry.lock:
            item.logs.append(
                f"[env-risk] high={high} medium={medium} — check UI warnings / fingerprint-check"
            )
    return view


def resolve_user_data_dir(raw: str) -> Path:
    """Resolve relative profile dirs under APPDATA profiles root."""
    value = (raw or "").strip()
    if not value:
        return PROFILES_DIR / "unnamed"
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = PROFILES_DIR / path
    return path


def normalize_profile_paths(profile: Profile) -> Profile:
    """Ensure user_data_dir is absolute under the app data directory when relative."""
    if not profile.user_data_dir:
        return profile
    resolved = resolve_user_data_dir(profile.user_data_dir)
    if str(resolved) != profile.user_data_dir:
        data = profile.model_dump()
        data["user_data_dir"] = str(resolved)
        return Profile(**data)
    return profile


def validate_profile_for_launch(profile: Profile) -> list[str]:
    """Validate profile before launching. Returns list of error messages."""
    errors: list[str] = []
    engine = normalize_engine_name(getattr(profile, "engine", None))

    # 1. Camoufox binary only required for camoufox engine
    if engine == "camoufox":
        try:
            path_result = camoufox_path_info()
            if not path_result.get("ok") or not path_result.get("stdout", "").strip():
                errors.append("Camoufox browser binary not found. Complete first-run setup / fetch first.")
            else:
                browser_path = Path(path_result["stdout"].strip())
                if not browser_path.exists():
                    errors.append(f"Camoufox browser path does not exist: {browser_path}")
        except Exception as exc:
            errors.append(f"Failed to check Camoufox browser path: {exc}")

    # 2. Check user data directory is writable (if persistent context)
    if profile.persistent_context and profile.user_data_dir:
        user_data_dir = resolve_user_data_dir(profile.user_data_dir)
        try:
            user_data_dir.mkdir(parents=True, exist_ok=True)
            test_file = user_data_dir / ".write_test"
            test_file.write_text("test", encoding="utf-8")
            test_file.unlink()
        except PermissionError:
            errors.append(f"User data directory is not writable: {user_data_dir}")
        except OSError as exc:
            errors.append(f"Cannot access user data directory {user_data_dir}: {exc}")

    # 3. Validate proxy format
    if profile.proxy and profile.proxy.server:
        server = profile.proxy.server.strip()
        allowed_schemes = ("http://", "https://", "socks4://", "socks5://")
        if server and not server.lower().startswith(allowed_schemes):
            errors.append(f"Proxy server must use http://, https://, socks4://, or socks5:// (got: {server})")

    # 4. Validate startup URL
    if profile.startup_url:
        url = profile.startup_url.strip()
        if url and not url.startswith(("http://", "https://", "about:")):
            errors.append(f"Startup URL must start with http://, https://, or about: (got: {url})")

    # 5. Check if profile name is valid
    if not profile.name or not profile.name.strip():
        errors.append("Profile name cannot be empty")

    # 6. Engine constraints (Phase A / C)
    if engine == "chromium" and (profile.mode or "").lower() == "server":
        errors.append("Chromium engine does not support server mode in Phase A (use mode=browser)")
    if engine == "chromium":
        backend = normalize_chromium_backend_name(getattr(profile, "chromium_backend", None))
        if backend == "patchright" and not import_available("patchright"):
            errors.append(
                "patchright is not installed (required for chromium_backend=patchright). "
                f"Run: {chromium_install_hint('patchright')}"
            )
        elif backend == "playwright" and not import_available("playwright"):
            errors.append(
                "playwright is not installed (required for chromium_backend=playwright). "
                f"Run: {chromium_install_hint('playwright')}"
            )
        elif backend == "auto" and not (
            import_available("patchright") or import_available("playwright")
        ):
            errors.append(
                "neither patchright nor playwright is installed (required for chromium). "
                f"Run: {chromium_install_hint('auto')}"
            )
        channel = (getattr(profile, "chromium_channel", None) or "").strip()
        if channel == "chrome" and not detect_google_chrome_install().get("installed"):
            errors.append(
                "chromium_channel=chrome but Google Chrome was not found. "
                "Install Chrome or set channel to empty (bundled Chromium)."
            )
    if engine == "camoufox" and not import_available("camoufox"):
        # Soft: binary check already above; package import still useful
        pass

    # 7. user_data_dir must not be shared across engines (path marker convention)
    ud = (profile.user_data_dir or "").replace("\\", "/").lower()
    if engine == "chromium" and "/camoufox" in ud and "chromium" not in ud:
        errors.append(
            "user_data_dir looks like a camoufox profile path; use a separate directory for chromium "
            "(e.g. .../profiles/<name>-chromium)"
        )
    if engine == "camoufox" and "-chromium" in ud:
        errors.append(
            "user_data_dir looks like a chromium profile path; use a separate directory for camoufox"
        )

    # Phase B consistency hard checks (always)
    sw = int(getattr(profile, "screen_width", 0) or 0)
    sh = int(getattr(profile, "screen_height", 0) or 0)
    if (sw > 0) ^ (sh > 0):
        errors.append("screen_width and screen_height must both be set or both empty")
    ua = (getattr(profile, "user_agent", "") or "").strip()
    if ua and len(ua) < 20:
        errors.append("user_agent looks too short")
    if ua and "HeadlessChrome" in ua:
        errors.append("user_agent must not contain HeadlessChrome")

    # Phase B strict policy: promote high environment risks to launch errors
    policy = (getattr(profile, "consistency_policy", None) or "normal").strip().lower()
    if policy == "strict":
        for risk in environment_risks_for_profile(profile):
            if risk.get("level") == "high":
                errors.append(f"[strict] {risk.get('code')}: {risk.get('message')}")

    return errors


def detect_google_chrome_install() -> dict[str, Any]:
    """Best-effort local Google Chrome path detection (Windows-focused). Not a guarantee."""
    candidates: list[Path] = []
    env_candidates = [
        os.environ.get("PROGRAMFILES", ""),
        os.environ.get("PROGRAMFILES(X86)", ""),
        os.environ.get("LOCALAPPDATA", ""),
    ]
    for root in env_candidates:
        if not root:
            continue
        base = Path(root)
        candidates.extend(
            [
                base / "Google" / "Chrome" / "Application" / "chrome.exe",
                base / "Google" / "Chrome Beta" / "Application" / "chrome.exe",
            ]
        )
    # macOS / Linux common paths (harmless if missing)
    candidates.extend(
        [
            Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            Path("/usr/bin/google-chrome"),
            Path("/usr/bin/google-chrome-stable"),
            Path("/usr/bin/chromium"),
            Path("/usr/bin/chromium-browser"),
        ]
    )
    found: list[str] = []
    for path in candidates:
        try:
            if path.is_file():
                found.append(str(path))
        except OSError:
            continue
    return {"installed": bool(found), "paths": found[:5]}


def environment_risks_for_profile(profile: Profile) -> list[dict[str, str]]:
    """Soft warnings for high-risk site environments (not hard errors).

    These do **not** guarantee pass rates (payment, AI signup/subscribe, etc.).
    """
    risks: list[dict[str, str]] = []

    def add(code: str, level: str, message: str) -> None:
        risks.append({"code": code, "level": level, "message": message})

    tags = {str(t).lower() for t in (getattr(profile, "tags", None) or [])}
    ai_scene = bool(tags & {"ai", "chatgpt", "claude", "gemini", "openai", "anthropic"})

    engine = normalize_engine_name(getattr(profile, "engine", None))
    if engine == "chromium":
        backend_req = normalize_chromium_backend_name(getattr(profile, "chromium_backend", None))
        try:
            backend_eff = resolve_chromium_backend(backend_req)
        except Exception:
            backend_eff = backend_req
        if backend_eff == "patchright":
            add(
                "engine_chromium_phase_c_patchright",
                "low",
                "Chromium backend=patchright (Phase C). Improves automation concealment vs stock Playwright; still not a Multilogin-class or signup guarantee.",
            )
        else:
            add(
                "engine_chromium_playwright",
                "medium",
                "Chromium backend=playwright. Automation signals (e.g. webdriver) are more likely; prefer chromium_backend=auto/patchright when installed.",
            )
            if backend_req == "auto" and not import_available("patchright"):
                add(
                    "patchright_not_installed",
                    "medium",
                    "patchright not installed; auto fell back to playwright. Install: pip install patchright && patchright install chromium",
                )
        channel = (getattr(profile, "chromium_channel", None) or "").strip()
        chrome = detect_google_chrome_install()
        if not channel:
            if chrome.get("installed"):
                add(
                    "chromium_bundled_build",
                    "low",
                    "Using bundled Chromium (not channel=chrome). Google Chrome detected on this machine — optional: set chromium_channel=chrome.",
                )
            else:
                add(
                    "chromium_bundled_build",
                    "low",
                    "Using bundled Chromium build (not channel=chrome). Optional if Chrome is installed later.",
                )
        elif channel == "chrome" and not chrome.get("installed"):
            add(
                "chrome_channel_missing",
                "high",
                "chromium_channel=chrome but Google Chrome was not found in common install paths.",
            )
    else:
        add(
            "engine_firefox_payment_stack",
            "medium",
            "Camoufox is Firefox-based; many Chromium-oriented sites (checkout / some AI flows) score Chromium stacks more leniently.",
        )

    if profile.headless:
        add(
            "headless",
            "high",
            "Headless mode is commonly blocked by payment / 3DS / interactive signup flows. Use a visible browser window.",
        )
    if (profile.mode or "").lower() == "server":
        add(
            "server_mode",
            "high",
            "Server mode is for automation endpoints, not interactive signup/subscribe UIs.",
        )
    if ai_scene and engine != "chromium":
        add(
            "ai_scene_prefer_chromium",
            "medium",
            "AI-tagged profile on Camoufox/Firefox. Many users prefer Chromium + patchright for ChatGPT/Claude/Gemini-style flows (still no guarantee).",
        )
    if ai_scene and not profile.persistent_context:
        add(
            "ai_scene_no_persistent",
            "high",
            "AI workstation-style use usually needs persistent_context so cookies/session survive restarts.",
        )
    if profile.block_webgl:
        add(
            "block_webgl",
            "high",
            "Blocking WebGL removes GPU signals many checkout pages expect.",
        )
    if profile.block_images:
        add(
            "block_images",
            "medium",
            "Blocking images can break CAPTCHA / 3DS challenge pages.",
        )
    has_proxy = bool((profile.proxy and profile.proxy.server) or profile.proxy_id)
    if not has_proxy:
        add(
            "no_proxy",
            "medium",
            "No proxy configured. Exit IP will be your real network; payment risk engines often weight IP reputation heavily.",
        )
    if has_proxy and not profile.geoip:
        if engine == "chromium":
            # Chromium worker does not auto-geoip; timezone/locale must be set manually.
            if not (profile.timezone or "").strip() or not (profile.locale or "").strip():
                add(
                    "proxy_without_geoip",
                    "high",
                    "Chromium + proxy without geoip: set timezone and locale to match the exit IP (geoip auto is Camoufox-oriented).",
                )
            else:
                add(
                    "proxy_without_geoip",
                    "low",
                    "Chromium engine ignores Camoufox geoip; timezone/locale are set explicitly (good).",
                )
        else:
            add(
                "proxy_without_geoip",
                "high",
                "Proxy is set but geoip is off — timezone/locale may not match the exit IP (common hard-fail for checkout).",
            )
    if has_proxy and not (profile.timezone or "").strip():
        add(
            "proxy_without_timezone",
            "medium",
            "Proxy without explicit timezone. Prefer a timezone that matches the proxy region (or enable geoip).",
        )
    if has_proxy and not (profile.locale or "").strip():
        add(
            "proxy_without_locale",
            "medium",
            "Proxy without explicit locale/language. Align Accept-Language with the proxy region.",
        )
    if not profile.block_webrtc and profile.webrtc_mode == "default":
        add(
            "webrtc_leak_risk",
            "high",
            "WebRTC is not blocked — real local/public IPs may leak beside the proxy.",
        )
    if engine == "chromium" and profile.webrtc_mode == "force_proxy":
        add(
            "webrtc_force_proxy_chromium",
            "medium",
            "Chromium Phase B cannot fully force WebRTC through proxy at kernel level; prefer webrtc_mode=disable + block_webrtc.",
        )
    fonts = list(getattr(profile, "fonts", None) or [])
    font_pack = (getattr(profile, "font_pack", None) or "").strip()
    if engine == "chromium" and not fonts and not font_pack:
        add(
            "fonts_unset",
            "medium",
            "No fonts list / font_pack. Commercial stacks usually pin an OS font set for consistency.",
        )
    media = (getattr(profile, "media_devices", None) or "default").strip().lower()
    if engine == "chromium" and media == "default":
        add(
            "media_devices_default",
            "low",
            "media_devices=default leaves host enumerateDevices as-is (may be empty or odd on servers). Prefer random for desktop-like.",
        )
    if media == "empty":
        add(
            "media_devices_empty",
            "medium",
            "media_devices=empty is common on headless/VPS fingerprints; unusual for consumer desktop checkout.",
        )
    if not profile.persistent_context:
        add(
            "no_persistent",
            "medium",
            "Non-persistent context looks like a fresh automation profile (no cookies/history warm-up).",
        )
    if engine == "camoufox" and not profile.humanize:
        add(
            "no_humanize",
            "low",
            "Humanize is off; pointer/scroll patterns may look more robotic.",
        )
    if engine == "chromium" and profile.humanize:
        add(
            "humanize_chromium_noop",
            "info",
            "humanize is Camoufox-oriented; Chromium worker does not apply Camoufox humanize.",
        )
    if profile.screen_width and profile.screen_height:
        if profile.screen_width < 1024 or profile.screen_height < 700:
            add(
                "small_viewport",
                "medium",
                f"Viewport {profile.screen_width}x{profile.screen_height} is unusual for desktop checkout.",
            )
    if not (profile.webgl_vendor or "").strip() and not profile.block_webgl:
        add(
            "webgl_unset",
            "low",
            "WebGL vendor/renderer not pinned; Camoufox defaults apply (usually fine, but less reproducible).",
        )
    if (profile.os or "auto") == "auto":
        add(
            "os_auto",
            "low",
            "OS is auto. For payment flows, pin windows/macos to match the proxy and WebGL story.",
        )
    # Locale vs timezone rough consistency (same map as fingerprint-check).
    if profile.locale and profile.timezone:
        locale_tz_map = {
            "en-US": "America/",
            "en-GB": "Europe/London",
            "de-DE": "Europe/",
            "fr-FR": "Europe/",
            "ja-JP": "Asia/Tokyo",
            "zh-CN": "Asia/Shanghai",
            "zh-TW": "Asia/Taipei",
            "ko-KR": "Asia/Seoul",
        }
        matched = False
        for loc_prefix, tz_prefix in locale_tz_map.items():
            if profile.locale.startswith(loc_prefix) and profile.timezone.startswith(tz_prefix):
                matched = True
                break
        if not matched:
            add(
                "locale_timezone_mismatch",
                "medium",
                f"Locale ({profile.locale}) and timezone ({profile.timezone}) look inconsistent.",
            )

    add(
        "no_guarantee",
        "info",
        "FoxDesk cannot guarantee payment, AI signup/subscribe, or anti-bot pass rates. Internal quality only — not Multilogin/GoLogin SLA.",
    )
    return risks


@app.get("/api/sessions")
def list_sessions() -> list[dict[str, Any]]:
    return registry.list("session")


@app.post("/api/processes/{process_id}/stop")
def stop_process(process_id: str) -> dict[str, Any]:
    try:
        registry.stop(process_id)
        return registry.get(process_id).view()
    except KeyError:
        raise HTTPException(status_code=404, detail="process not found") from None


# --- Proxy Test ---
def _socks5_connect(
    proxy_host: str,
    proxy_port: int,
    target_host: str,
    target_port: int,
    timeout: float = 10.0,
    username: str = "",
    password: str = "",
) -> socket.socket:
    """Raw SOCKS5 CONNECT handshake with optional username/password auth."""
    import socket as _sock

    sock = _sock.create_connection((proxy_host, proxy_port), timeout=timeout)
    if username:
        # Offer user/pass auth
        sock.sendall(b"\x05\x02\x00\x02")
    else:
        sock.sendall(b"\x05\x01\x00")
    resp = sock.recv(2)
    if len(resp) < 2 or resp[0] != 0x05:
        sock.close()
        raise ConnectionError("SOCKS5 proxy greeting failed")
    method = resp[1]
    if method == 0x02:
        u = username.encode("utf-8")[:255]
        p = password.encode("utf-8")[:255]
        sock.sendall(b"\x01" + bytes([len(u)]) + u + bytes([len(p)]) + p)
        auth_resp = sock.recv(2)
        if len(auth_resp) < 2 or auth_resp[1] != 0x00:
            sock.close()
            raise ConnectionError("SOCKS5 username/password authentication failed")
    elif method != 0x00:
        sock.close()
        raise ConnectionError(f"SOCKS5 proxy auth negotiation failed (method={method})")
    # CONNECT request
    addr = target_host.encode("ascii")
    req = b"\x05\x01\x00\x03" + bytes([len(addr)]) + addr + target_port.to_bytes(2, "big")
    sock.sendall(req)
    resp = sock.recv(4)
    if len(resp) < 4 or resp[1] != 0x00:
        sock.close()
        raise ConnectionError(f"SOCKS5 CONNECT failed: error code {resp[1] if len(resp) > 1 else 'unknown'}")
    # Drain bind addr
    atyp = resp[3] if len(resp) > 3 else 1
    if atyp == 1:
        sock.recv(4 + 2)
    elif atyp == 3:
        ln = sock.recv(1)
        if ln:
            sock.recv(ln[0] + 2)
    elif atyp == 4:
        sock.recv(16 + 2)
    return sock


def _socks4_connect(proxy_host: str, proxy_port: int, target_host: str, target_port: int, timeout: float = 10.0) -> socket.socket:
    """Raw SOCKS4 CONNECT handshake."""
    import socket as _sock
    import struct
    sock = _sock.create_connection((proxy_host, proxy_port), timeout=timeout)
    ip_parts = target_host.split(".")
    if len(ip_parts) == 4:
        ip_bytes = bytes(int(p) for p in ip_parts)
    else:
        raise ConnectionError("SOCKS4 requires IPv4 target for CONNECT")
    req = b"\x04\x01" + struct.pack("!H", target_port) + ip_bytes + b"\x00"
    sock.sendall(req)
    resp = sock.recv(8)
    if len(resp) < 2 or resp[1] != 0x5A:
        sock.close()
        raise ConnectionError(f"SOCKS4 CONNECT failed: code {resp[1] if len(resp) > 1 else 'unknown'}")
    return sock


def _test_proxy_connection(proxy_url: str, username: str = "", password: str = "", timeout: float = 10.0) -> dict[str, Any]:
    """Test proxy by connecting through it to an IP-check endpoint."""
    import time as _time
    from urllib.parse import quote, urlparse
    from urllib.request import ProxyHandler, Request, build_opener

    parsed = urlparse(proxy_url)
    scheme = parsed.scheme.lower()
    host = parsed.hostname or ""
    port = parsed.port or (1080 if "socks" in scheme else 8080)
    user = username or (parsed.username or "")
    pwd = password if password is not None else (parsed.password or "")

    start = _time.monotonic()
    try:
        if scheme in ("http", "https"):
            if user:
                auth = f"{quote(user, safe='')}:{quote(pwd or '', safe='')}@"
            else:
                auth = ""
            proxy_with_auth = f"{scheme}://{auth}{host}:{port}"
            proxy_handler = ProxyHandler({"http": proxy_with_auth, "https": proxy_with_auth})
            opener = build_opener(proxy_handler)
            req = Request("http://httpbin.org/ip")
            resp = opener.open(req, timeout=timeout)
            data = json.loads(resp.read())
            ip = data.get("origin", "unknown")
        elif scheme == "socks5":
            sock = _socks5_connect(host, port, "httpbin.org", 80, timeout=timeout, username=user, password=pwd or "")
            sock.sendall(b"GET /ip HTTP/1.1\r\nHost: httpbin.org\r\nConnection: close\r\n\r\n")
            response = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk
            sock.close()
            body = response.split(b"\r\n\r\n", 1)[-1] if b"\r\n\r\n" in response else b"{}"
            data = json.loads(body)
            ip = data.get("origin", "unknown")
        elif scheme == "socks4":
            sock = _socks4_connect(host, port, "httpbin.org", 80, timeout=timeout)
            sock.sendall(b"GET /ip HTTP/1.1\r\nHost: httpbin.org\r\nConnection: close\r\n\r\n")
            response = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk
            sock.close()
            body = response.split(b"\r\n\r\n", 1)[-1] if b"\r\n\r\n" in response else b"{}"
            data = json.loads(body)
            ip = data.get("origin", "unknown")
        else:
            return {"ok": False, "error": f"Unsupported proxy scheme: {scheme}", "latency_ms": None, "exit_ip": None}

        latency = int((_time.monotonic() - start) * 1000)
        return {"ok": True, "exit_ip": ip, "latency_ms": latency, "scheme": scheme}
    except Exception as exc:
        latency = int((_time.monotonic() - start) * 1000)
        return {"ok": False, "error": str(exc), "latency_ms": latency, "exit_ip": None, "scheme": scheme}


@app.post("/api/proxy/test")
def proxy_test(request: ProxyTestRequest) -> dict[str, Any]:
    server = request.server.strip()
    if not server:
        raise HTTPException(status_code=400, detail="proxy server is required")
    if "://" not in server:
        server = f"http://{server}"
    return _test_proxy_connection(server, request.username, request.password)


# --- Channels ---
@app.get("/api/channels")
def list_channels() -> list[dict[str, Any]]:
    return channel_store.all()


@app.put("/api/channels")
def update_channel(request: ChannelUpdateRequest) -> dict[str, bool]:
    channel_store.update(request.id, request.prefix)
    return {"ok": True}


@app.post("/api/channels/{channel_id}/fetch")
def channel_fetch(channel_id: str, request: TaskRequest | None = None) -> dict[str, Any]:
    channels = channel_store.all()
    channel = next((ch for ch in channels if ch["id"] == channel_id), None)
    if not channel:
        raise HTTPException(status_code=404, detail="channel not found")
    # Prefer guided/in-process fetch — works for frozen builds and mirror selection.
    result = setup_manager.start(channel=channel_id or "github", auto=True, force=True)
    return {
        "id": f"setup-{int(time.time() * 1000)}",
        "kind": "task",
        "label": f"fetch ({channel['name']})",
        "status": "running" if result.get("status") == "running" else result.get("status"),
        "returncode": None,
        "logs": result.get("logs") or [f"started guided fetch via {channel_id}"],
        "ok": result.get("status") != "failed",
        "setup": result,
    }


# --- Session Detail ---
@app.get("/api/sessions/{process_id}")
def get_session(process_id: str) -> dict[str, Any]:
    try:
        item = registry.get(process_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="session not found") from None
    view = item.view()
    view["started_at_human"] = datetime.fromtimestamp(item.started_at, tz=timezone.utc).isoformat()
    view["uptime_seconds"] = int(time.time() - item.started_at)
    # Prefer runtime id recorded in logs; fallback to profile id/name match
    runtime_name = None
    for line in reversed(item.logs):
        if line.startswith("[runtime] "):
            runtime_name = line.replace("[runtime] ", "", 1).strip()
            break
    if runtime_name:
        runtime_file = RUNTIME_DIR / runtime_name
        if runtime_file.exists():
            try:
                view["profile_snapshot"] = json.loads(runtime_file.read_text(encoding="utf-8"))
                return view
            except Exception:
                pass
    for runtime_file in RUNTIME_DIR.glob("*.json"):
        try:
            data = json.loads(runtime_file.read_text(encoding="utf-8"))
            if data.get("name") == item.label or data.get("id") and data.get("name") == item.label:
                view["profile_snapshot"] = data
                break
        except Exception:
            continue
    return view


@app.api_route("/api/sessions/{process_id}/logs/download", methods=["GET", "POST"])
def download_session_logs(process_id: str):
    from fastapi.responses import PlainTextResponse
    try:
        item = registry.get(process_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="session not found") from None
    log_text = "\n".join(item.logs)
    return PlainTextResponse(
        log_text,
        headers={"Content-Disposition": f"attachment; filename=session-{process_id[:8]}.log"},
    )


# --- Batch Operations ---
MAX_CONCURRENT_SESSIONS = 5


@app.post("/api/sessions/batch")
def batch_launch(request: BatchLaunchRequest) -> dict[str, Any]:
    current_sessions = registry.list("session")
    running = sum(1 for s in current_sessions if s["status"] == "running")
    available = MAX_CONCURRENT_SESSIONS - running
    if available <= 0:
        raise HTTPException(status_code=409, detail=f"Max {MAX_CONCURRENT_SESSIONS} concurrent sessions reached")
    results = []
    started = 0
    failed = 0
    for profile_id in request.profile_ids[:available]:
        try:
            profile = store.get(profile_id)
        except KeyError:
            results.append({"profile_id": profile_id, "ok": False, "error": "profile not found"})
            failed += 1
            continue
        profile = apply_proxy_pool_to_profile(profile)
        profile = normalize_profile_paths(profile)
        engine = normalize_engine_name(getattr(profile, "engine", None))
        if engine == "camoufox" and not import_available("camoufox"):
            results.append({"profile_id": profile_id, "ok": False, "error": "camoufox is not installed"})
            failed += 1
            continue
        resolved_backend = None
        if engine == "chromium":
            try:
                resolved_backend = resolve_chromium_backend(getattr(profile, "chromium_backend", None))
            except Exception as exc:
                results.append({"profile_id": profile_id, "ok": False, "error": str(exc)})
                failed += 1
                continue
        errors = validate_profile_for_launch(profile)
        if errors:
            results.append({"profile_id": profile_id, "ok": False, "error": "; ".join(errors)})
            failed += 1
            continue
        if profile.persistent_context and profile.user_data_dir:
            Path(profile.user_data_dir).expanduser().mkdir(parents=True, exist_ok=True)
        runtime_id = str(uuid.uuid4())
        runtime_path = RUNTIME_DIR / f"{runtime_id}.json"
        payload = profile.model_dump()
        payload["engine"] = engine
        if resolved_backend:
            payload["chromium_backend"] = resolved_backend
        payload["_runtime_id"] = runtime_id
        payload["_profile_id"] = profile.id
        runtime_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        runtime_path.with_suffix(".cmd.jsonl").write_text("", encoding="utf-8")
        runtime_path.with_suffix(".result.jsonl").write_text("", encoding="utf-8")
        command = worker_command(runtime_path, engine=engine)
        item = start_process(
            "session",
            profile.name,
            command,
            profile_id=profile.id,
            runtime_id=runtime_id,
            runtime_path=str(runtime_path),
            mode=profile.mode,
            engine=engine,
        )
        results.append(
            {
                "profile_id": profile_id,
                "ok": True,
                "process_id": item.id,
                "runtime_id": runtime_id,
                "engine": engine,
                "chromium_backend": resolved_backend,
            }
        )
        started += 1
    skipped = len(request.profile_ids) - available
    activity.log("session_batch_launch", f"started={started} failed={failed} skipped={max(0, skipped)}")
    return {"started": started, "failed": failed, "skipped": max(0, skipped), "results": results}


@app.post("/api/sessions/batch-stop")
def batch_stop(request: BatchStopRequest) -> dict[str, Any]:
    stopped = 0
    missing = 0
    for pid in request.process_ids:
        try:
            registry.stop(pid)
            stopped += 1
        except KeyError:
            missing += 1
    activity.log("session_batch_stop", f"stopped={stopped} missing={missing}")
    return {"stopped": stopped, "missing": missing, "requested": len(request.process_ids)}


# --- Random Fingerprint Generation ---
COMMON_TIMEZONES = [
    "America/New_York", "America/Chicago", "America/Los_Angeles", "America/Denver",
    "Europe/London", "Europe/Berlin", "Europe/Paris", "Europe/Moscow",
    "Asia/Tokyo", "Asia/Shanghai", "Asia/Seoul", "Asia/Kolkata",
    "Australia/Sydney", "Pacific/Auckland",
]

WINDOWS_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
]

MACOS_USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
]

LINUX_USER_AGENTS = [
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0",
]

WEBGL_VENDORS = ["Google Inc. (NVIDIA)", "Google Inc. (AMD)", "Google Inc. (Intel)", "Apple Inc."]
WEBGL_RENDERERS = [
    "ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 SUPER Direct3D11 vs_5_0 ps_5_0)",
    "ANGLE (AMD, AMD Radeon RX 580 Direct3D11 vs_5_0 ps_5_0)",
    "ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0)",
    "Apple GPU",
]

SCREEN_CONFIGS = [
    (1920, 1080, 24, 1.0),
    (2560, 1440, 24, 1.0),
    (1366, 768, 24, 1.0),
    (1536, 864, 24, 1.25),
    (1440, 900, 24, 1.0),
    (3840, 2160, 24, 1.5),
    (1280, 720, 24, 1.0),
]

LOCALES = ["en-US", "en-GB", "de-DE", "fr-FR", "es-ES", "ja-JP", "zh-CN", "zh-TW", "ko-KR", "pt-BR", "ru-RU", "it-IT"]

WEBRTC_MODES = ["default", "disable", "public_only", "force_proxy"]
MEDIA_MODES = ["default", "random", "empty"]


@app.post("/api/fingerprint/generate")
def generate_fingerprint(target_os: str = "auto") -> dict[str, Any]:
    """Generate a randomized fingerprint profile."""
    import random as _rand
    os_choice = _rand.choice(["windows", "macos", "linux"]) if target_os == "auto" else target_os
    if os_choice == "windows":
        ua = _rand.choice(WINDOWS_USER_AGENTS)
        platform_str = "Win32"
        vendor_str = "Google Inc."
    elif os_choice == "macos":
        ua = _rand.choice(MACOS_USER_AGENTS)
        platform_str = "MacIntel"
        vendor_str = "Apple Computer, Inc."
    else:
        ua = _rand.choice(LINUX_USER_AGENTS)
        platform_str = "Linux x86_64"
        vendor_str = "Google Inc."

    screen = _rand.choice(SCREEN_CONFIGS)
    locale = _rand.choice(LOCALES)
    timezone = _rand.choice(COMMON_TIMEZONES)

    from backend.fingerprint_presets import FONT_PACKS, normalize_os_key

    pack_key = normalize_os_key(os_choice)
    return {
        "navigator_platform": platform_str,
        "navigator_vendor": vendor_str,
        "screen_width": screen[0],
        "screen_height": screen[1],
        "screen_color_depth": screen[2],
        "device_pixel_ratio": screen[3],
        "hardware_concurrency": _rand.choice([4, 6, 8, 12, 16]),
        "device_memory": _rand.choice([4, 8, 16]),
        "canvas_noise": True,
        "webgl_vendor": _rand.choice(WEBGL_VENDORS),
        "webgl_renderer": _rand.choice(WEBGL_RENDERERS),
        "audio_noise": True,
        "font_pack": pack_key,
        "fonts": list(FONT_PACKS.get(pack_key, [])),
        "timezone": timezone,
        "locale": locale,
        "webrtc_mode": "disable",
        "media_devices": "random",
        "user_agent": ua,
        "ua_ch_platform": "Windows" if os_choice == "windows" else ("macOS" if os_choice == "macos" else "Linux"),
        "ua_ch_mobile": False,
        "consistency_policy": "normal",
    }


# --- Cookie Management ---
def _find_cookies_sqlite(user_data_dir: Path) -> Path | None:
    candidates = [
        user_data_dir / "cookies.sqlite",
        user_data_dir / "cookies.sqlite.corrupted",
    ]
    # Firefox-style nested profiles
    for path in user_data_dir.rglob("cookies.sqlite"):
        candidates.append(path)
    for path in candidates:
        if path.exists() and path.is_file():
            return path
    return None


@app.get("/api/profiles/{profile_id}/cookies")
def export_cookies(profile_id: str):
    from fastapi.responses import JSONResponse
    try:
        profile = store.get(profile_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="profile not found") from None
    if not profile.user_data_dir:
        raise HTTPException(status_code=409, detail="profile has no user_data_dir")
    user_data = Path(profile.user_data_dir).expanduser()
    imported_file = user_data / "imported_cookies.json"
    cookies_path = _find_cookies_sqlite(user_data)

    # Prefer live sqlite; fallback to previously imported JSON
    if cookies_path is None:
        if imported_file.exists():
            try:
                data = json.loads(imported_file.read_text(encoding="utf-8"))
                cookies = data if isinstance(data, list) else data.get("cookies", [])
                return JSONResponse({
                    "cookies": cookies,
                    "count": len(cookies),
                    "source": "imported_cookies.json",
                })
            except Exception as exc:
                raise HTTPException(status_code=500, detail=f"Failed to read imported cookies: {exc}") from None
        return JSONResponse({"cookies": [], "count": 0, "source": None})

    try:
        import sqlite3
        # Copy to temp to avoid Windows lock issues while browser is open
        tmp = RUNTIME_DIR / f"cookies-export-{uuid.uuid4().hex}.sqlite"
        shutil.copy2(cookies_path, tmp)
        try:
            conn = sqlite3.connect(str(tmp))
            cursor = conn.execute(
                "SELECT host, name, value, path, expiry, isSecure, isHttpOnly, sameSite FROM moz_cookies"
            )
            cookies = []
            for row in cursor.fetchall():
                cookies.append({
                    "host": row[0],
                    "domain": row[0],
                    "name": row[1],
                    "value": row[2],
                    "path": row[3],
                    "expires": row[4],
                    "secure": bool(row[5]),
                    "httpOnly": bool(row[6]),
                    "sameSite": row[7] or "Lax",
                })
            conn.close()
        finally:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
        return JSONResponse({
            "cookies": cookies,
            "count": len(cookies),
            "source": str(cookies_path),
        })
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read cookies: {exc}") from None


def _parse_netscape_cookies(text: str) -> list[dict[str, Any]]:
    cookies: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 7:
            continue
        domain, _flag, path, secure, expires, name, value = parts[:7]
        cookie: dict[str, Any] = {
            "domain": domain,
            "host": domain,
            "path": path or "/",
            "secure": str(secure).upper() == "TRUE",
            "expires": int(float(expires)) if expires not in ("", "0") else None,
            "name": name,
            "value": value,
            "httpOnly": domain.startswith("#HttpOnly_") or domain.startswith("."),
        }
        if cookie["domain"].startswith("#HttpOnly_"):
            cookie["domain"] = cookie["domain"].replace("#HttpOnly_", "", 1)
            cookie["host"] = cookie["domain"]
            cookie["httpOnly"] = True
        cookies.append(cookie)
    return cookies


@app.post("/api/profiles/{profile_id}/cookies")
def import_cookies(profile_id: str, request: dict[str, Any]):
    try:
        profile = store.get(profile_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="profile not found") from None
    if not profile.user_data_dir:
        raise HTTPException(status_code=409, detail="profile has no user_data_dir")

    cookies = request.get("cookies", [])
    raw_text = request.get("raw_text") or request.get("text") or ""
    if raw_text and not cookies:
        text = str(raw_text)
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                cookies = parsed
            elif isinstance(parsed, dict):
                cookies = parsed.get("cookies") or []
        except Exception:
            cookies = _parse_netscape_cookies(text)
    if not isinstance(cookies, list):
        raise HTTPException(status_code=400, detail="cookies must be a list or Netscape/JSON text")

    cookies_dir = Path(profile.user_data_dir).expanduser()
    cookies_dir.mkdir(parents=True, exist_ok=True)
    cookies_file = cookies_dir / "imported_cookies.json"
    cookies_file.write_text(json.dumps(cookies, ensure_ascii=False, indent=2), encoding="utf-8")
    activity.log("cookies_import", f"{profile.name}: {len(cookies)}")
    return {
        "ok": True,
        "count": len(cookies),
        "path": str(cookies_file),
        "note": "Cookies are applied on next session launch via Playwright add_cookies.",
    }


# --- Proxy Pool ---
class ProxyPoolIn(BaseModel):
    name: str = "Proxy"
    server: str
    username: str = ""
    password: str = ""
    tags: list[str] = Field(default_factory=list)
    notes: str = ""


class ProxyPoolImportRequest(BaseModel):
    lines: list[str]
    replace: bool = False


class ProxyAssignRequest(BaseModel):
    profile_ids: list[str]
    proxy_id: str = ""


@app.get("/api/proxies")
def list_proxies() -> list[dict[str, Any]]:
    return proxy_pool.all()


@app.post("/api/proxies")
def create_proxy(item: ProxyPoolIn) -> dict[str, Any]:
    try:
        created = proxy_pool.create(item.model_dump())
        activity.log("proxy_create", created.get("name") or created.get("server") or "")
        return created
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


@app.put("/api/proxies/{proxy_id}")
def update_proxy(proxy_id: str, item: ProxyPoolIn) -> dict[str, Any]:
    try:
        return proxy_pool.update(proxy_id, item.model_dump())
    except KeyError:
        raise HTTPException(status_code=404, detail="proxy not found") from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


@app.delete("/api/proxies/{proxy_id}")
def delete_proxy(proxy_id: str) -> dict[str, bool]:
    try:
        proxy_pool.delete(proxy_id)
        activity.log("proxy_delete", proxy_id)
        return {"ok": True}
    except KeyError:
        raise HTTPException(status_code=404, detail="proxy not found") from None


@app.post("/api/proxies/import")
def import_proxy_pool(request: ProxyPoolImportRequest) -> dict[str, Any]:
    imported = proxy_pool.import_lines(request.lines, replace=request.replace)
    activity.log("proxy_import", f"count={len(imported)}")
    return {"ok": True, "count": len(imported), "proxies": imported}


@app.post("/api/proxies/{proxy_id}/test")
def test_proxy_pool_item(proxy_id: str) -> dict[str, Any]:
    try:
        item = proxy_pool.get(proxy_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="proxy not found") from None
    result = _test_proxy_connection(item.get("server") or "", item.get("username") or "", item.get("password") or "")
    try:
        proxy_pool.mark_test_result(proxy_id, result)
    except KeyError:
        pass
    return result


@app.post("/api/proxies/assign")
def assign_proxy_to_profiles(request: ProxyAssignRequest) -> dict[str, Any]:
    if request.proxy_id:
        try:
            proxy_pool.get(request.proxy_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="proxy not found") from None
    profiles = store.all()
    updated = 0
    for idx, profile in enumerate(profiles):
        if profile.id not in request.profile_ids:
            continue
        dump = profile.model_dump()
        dump["proxy_id"] = request.proxy_id
        if request.proxy_id:
            item = proxy_pool.get(request.proxy_id)
            dump["proxy"] = {
                "server": item.get("server") or "",
                "username": item.get("username") or "",
                "password": item.get("password") or "",
            }
        dump["updated_at"] = now_iso()
        profiles[idx] = Profile(**dump)
        updated += 1
    store.save_all(profiles)
    activity.log("proxy_assign", f"updated={updated}")
    return {"ok": True, "updated": updated}


# --- Templates ---
@app.get("/api/templates")
def list_templates() -> list[dict[str, Any]]:
    return profile_templates()


@app.post("/api/templates/{template_id}/create")
def create_from_template(template_id: str) -> Profile:
    template = next((t for t in profile_templates() if t["id"] == template_id), None)
    if not template:
        raise HTTPException(status_code=404, detail="template not found")
    data = dict(template["profile"])
    slug = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in data.get("name", "template")).strip("-")
    engine = normalize_engine_name(data.get("engine"))
    # Isolate user_data per engine so camoufox/chromium never share a profile dir.
    suffix = "chromium" if engine == "chromium" else "camoufox"
    data["user_data_dir"] = str(PROFILES_DIR / f"{slug}-{suffix}-{uuid.uuid4().hex[:6]}")
    data.setdefault("proxy", {"server": "", "username": "", "password": ""})
    data.setdefault("proxy_id", "")
    data.setdefault("addons", [])
    data.setdefault("extra_args", [])
    data.setdefault("fonts", [])
    if engine == "chromium":
        data.setdefault("chromium_backend", "auto")
    created = store.create(ProfileIn(**data))
    activity.log("template_create", f"{template_id} -> {created.name} engine={engine}")
    return created


# --- Bulk Proxy Import ---
class BulkProxyRequest(BaseModel):
    proxies: list[str]
    profile_ids: list[str] = Field(default_factory=list)


@app.post("/api/profiles/bulk-proxy")
def bulk_proxy_import(request: BulkProxyRequest) -> dict[str, Any]:
    """Import proxies and assign to profiles. Format: one proxy per line, e.g. socks5://user:pass@host:port"""
    updated = 0
    profiles = store.all()
    target_ids = set(request.profile_ids) if request.profile_ids else {p.id for p in profiles}
    for i, proxy_str in enumerate(request.proxies):
        proxy_str = proxy_str.strip()
        if not proxy_str:
            continue
        if "://" not in proxy_str:
            proxy_str = f"http://{proxy_str}"
        # Find profile to update
        for profile in profiles:
            if profile.id in target_ids:
                idx = next((j for j, p in enumerate(profiles) if p.id == profile.id), None)
                if idx is not None:
                    dump = profile.model_dump()
                    dump["proxy"] = ProxyConfig(server=proxy_str).model_dump()
                    dump["updated_at"] = now_iso()
                    profiles[idx] = Profile(**dump)
                    updated += 1
                    target_ids.discard(profile.id)
                    break
        if not target_ids:
            break
    store.save_all(profiles)
    return {"ok": True, "updated": updated}


# --- Activity Log ---
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


@app.get("/api/activity")
def list_activity(limit: int = 100) -> list[dict[str, str]]:
    return activity.list(limit)


class NavigateRequest(BaseModel):
    url: str


class EvaluateRequest(BaseModel):
    expression: str = Field(min_length=1, max_length=1500)


class ScreenshotRequest(BaseModel):
    full_page: bool = False


def _session_command(process_id: str, cmd: str, payload: dict[str, Any] | None = None, timeout: float = 45.0) -> dict[str, Any]:
    try:
        item = registry.get(process_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="session not found") from exc
    if item.kind != "session":
        raise HTTPException(status_code=400, detail="not a browser session")
    if item.process.poll() is not None:
        raise HTTPException(status_code=409, detail="session is not running")
    if not item.runtime_path:
        raise HTTPException(status_code=409, detail="session has no runtime control channel")
    browser_only = {
        "navigate",
        "fingerprint",
        "probe",
        "screenshot",
        "shot",
        "evaluate",
        "eval",
    }
    if (item.mode or "").lower() == "server" and cmd in browser_only:
        raise HTTPException(
            status_code=409,
            detail="command only supported for browser-mode sessions (server mode exposes ws_endpoint instead)",
        )
    result = send_worker_command(item.runtime_path, cmd, payload=payload, timeout=timeout)
    item.touch()
    if result.get("ok") and isinstance(result.get("report"), dict):
        item.fingerprint_report = result.get("report")
    return {"ok": bool(result.get("ok")), "session_id": process_id, **result}


# --- Local API Service (for automation tools) ---
@app.get("/api/v1/sessions")
def api_v1_sessions() -> list[dict[str, Any]]:
    """Public API: list running sessions for automation tools."""
    return registry.list("session")


@app.post("/api/v1/sessions/{process_id}/navigate")
def api_v1_navigate(process_id: str, request: NavigateRequest) -> dict[str, Any]:
    """Live-navigate a running browser-mode session to a URL."""
    return _session_command(process_id, "navigate", {"url": request.url})


@app.post("/api/sessions/{process_id}/navigate")
def session_navigate(process_id: str, request: NavigateRequest) -> dict[str, Any]:
    result = _session_command(process_id, "navigate", {"url": request.url})
    activity.log("session_navigate", f"{process_id} -> {request.url}")
    return result


@app.post("/api/sessions/{process_id}/fingerprint")
def session_fingerprint_probe(process_id: str) -> dict[str, Any]:
    """Probe live fingerprint values from a running browser session."""
    result = _session_command(process_id, "fingerprint", timeout=60.0)
    activity.log("session_fingerprint", process_id)
    return result


@app.post("/api/sessions/{process_id}/screenshot")
def session_screenshot(process_id: str, request: ScreenshotRequest | None = None) -> dict[str, Any]:
    """Capture a PNG screenshot from a running browser-mode session (base64)."""
    body = request or ScreenshotRequest()
    result = _session_command(
        process_id,
        "screenshot",
        {"full_page": bool(body.full_page)},
        timeout=60.0,
    )
    activity.log("session_screenshot", process_id)
    return result


@app.post("/api/sessions/{process_id}/evaluate")
def session_evaluate(process_id: str, request: EvaluateRequest) -> dict[str, Any]:
    """Run a short browser-context expression (local automation helper; not a sandbox)."""
    result = _session_command(
        process_id,
        "evaluate",
        {"expression": request.expression},
        timeout=20.0,
    )
    activity.log("session_evaluate", process_id)
    return result


@app.post("/api/sessions/{process_id}/endpoint")
def session_refresh_endpoint(process_id: str) -> dict[str, Any]:
    """Ask a server-mode session for its current ws_endpoint (if known)."""
    try:
        item = registry.get(process_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="session not found") from exc
    if item.kind != "session":
        raise HTTPException(status_code=400, detail="not a browser session")
    if item.process.poll() is not None:
        raise HTTPException(status_code=409, detail="session is not running")
    if item.ws_endpoint:
        item.touch()
        return {"ok": True, "session_id": process_id, "ws_endpoint": item.ws_endpoint, "source": "registry"}
    if item.runtime_path:
        side = Path(item.runtime_path).with_suffix(".ws")
        try:
            if side.exists():
                ws = side.read_text(encoding="utf-8").strip()
                if ws:
                    item.ws_endpoint = ws
                    item.ready = True
                    item.touch()
                    return {"ok": True, "session_id": process_id, "ws_endpoint": ws, "source": "sidecar"}
        except OSError:
            pass
    if item.runtime_path:
        result = send_worker_command(item.runtime_path, "endpoint", timeout=10.0)
        item.touch()
        ws = result.get("ws_endpoint")
        if result.get("ok") and ws:
            item.ws_endpoint = str(ws)
            item.ready = True
            return {
                "ok": True,
                "session_id": process_id,
                "ws_endpoint": item.ws_endpoint,
                "source": "worker",
            }
        return {
            "ok": bool(result.get("ok")),
            "session_id": process_id,
            "ws_endpoint": item.ws_endpoint,
            "error": result.get("error") or "endpoint not available yet",
            "source": "worker",
        }
    return {"ok": False, "session_id": process_id, "error": "no runtime control channel"}


@app.get("/api/system/resources")
def system_resources() -> dict[str, Any]:
    """Lightweight process resource snapshot for the manager UI."""
    sessions = [s for s in registry.list("session") if str(s.get("status", "")).startswith("running") or s.get("status") == "running"]
    settings_view = settings_store.get()
    mem_mb = None
    cpu = None
    try:
        import psutil  # type: ignore

        proc = psutil.Process()
        mem_mb = round(proc.memory_info().rss / (1024 * 1024), 1)
        cpu = proc.cpu_percent(interval=0.05)
        # include children roughly
        for child in proc.children(recursive=True):
            try:
                mem_mb += round(child.memory_info().rss / (1024 * 1024), 1)
            except Exception:
                pass
    except Exception:
        # Fallback: no psutil — still return session counts.
        pass
    return {
        "ok": True,
        "running_sessions": len(sessions),
        "max_concurrent_sessions": settings_view.get("max_concurrent_sessions"),
        "idle_session_minutes": settings_view.get("idle_session_minutes"),
        "manager_memory_mb": mem_mb,
        "manager_cpu_percent": cpu,
        "sessions": [
            {
                "id": s.get("id"),
                "label": s.get("label"),
                "pid": s.get("pid"),
                "mode": s.get("mode"),
                "ready": s.get("ready"),
                "ws_endpoint": s.get("ws_endpoint"),
                "idle_seconds": s.get("idle_seconds"),
            }
            for s in sessions
        ],
    }


class BackupRequest(BaseModel):
    password: str = Field(min_length=4, max_length=128)
    include_profiles_dirs: bool = False


class BackupRestoreRequest(BaseModel):
    password: str = Field(min_length=4, max_length=128)
    path: str = Field(min_length=1, max_length=1024)
    # When true, write restored files over current data_dir (after pre-restore snapshot).
    overwrite: bool = True
    # Restore only listed names; empty = all safe names in archive.
    include: list[str] = Field(default_factory=list)


_BACKUP_SAFE_ROOT_NAMES = {
    "profiles.json",
    "proxies.json",
    "settings.json",
    "channels.json",
    "activity.json",
}


def _collect_backup_files(*, include_profiles_dirs: bool) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    for name in sorted(_BACKUP_SAFE_ROOT_NAMES):
        p = DATA_DIR / name
        if p.exists() and p.is_file():
            files[name] = p.read_bytes()
    if include_profiles_dirs and PROFILES_DIR.exists():
        for p in PROFILES_DIR.rglob("*"):
            if not p.is_file():
                continue
            if p.stat().st_size > 8 * 1024 * 1024:
                continue
            rel = p.relative_to(PROFILES_DIR)
            if ".." in rel.parts:
                continue
            arc = str(Path("profiles") / rel).replace("\\", "/")
            files[arc] = p.read_bytes()
    return files


def _safe_restore_target(arcname: str) -> Path | None:
    """Map archive name to absolute path under DATA_DIR, or None if unsafe."""
    name = (arcname or "").replace("\\", "/").lstrip("/")
    if not name or name.startswith("../") or "/../" in f"/{name}/":
        return None
    if name in _BACKUP_SAFE_ROOT_NAMES:
        return DATA_DIR / name
    if name.startswith("profiles/"):
        rel = name[len("profiles/") :]
        if not rel or ".." in Path(rel).parts:
            return None
        return PROFILES_DIR / rel
    return None


@app.get("/api/system/backups")
def list_backups() -> dict[str, Any]:
    backups = DATA_DIR / "backups"
    backups.mkdir(parents=True, exist_ok=True)
    items: list[dict[str, Any]] = []
    for p in sorted(backups.glob("foxdesk-backup-*"), reverse=True):
        if not p.is_file():
            continue
        try:
            st = p.stat()
            kind = "encrypted" if p.suffix.lower() == ".fdk" else ("zip" if p.suffix.lower() == ".zip" else "file")
            items.append(
                {
                    "name": p.name,
                    "path": str(p),
                    "size": st.st_size,
                    "mtime": st.st_mtime,
                    "kind": kind,
                }
            )
        except OSError:
            continue
    return {"ok": True, "items": items[:100], "dir": str(backups)}


@app.post("/api/system/backup")
def create_encrypted_backup(request: BackupRequest) -> dict[str, Any]:
    """Export core config into a password-encrypted `.fdk` package under data_dir/backups."""
    from backend.backup_crypto import write_encrypted_backup

    backups = DATA_DIR / "backups"
    backups.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = backups / f"foxdesk-backup-{stamp}.fdk"
    files = _collect_backup_files(include_profiles_dirs=request.include_profiles_dirs)
    if not files:
        raise HTTPException(status_code=400, detail="nothing to back up")
    meta = {
        "app_version": APP_VERSION,
        "created_at": now_iso(),
        "files": sorted(files.keys()),
        "format": "foxdesk-backup-v1",
        "note": "Password-based encrypt-then-MAC package (PBKDF2 + HMAC). Keep offline.",
    }
    try:
        write_encrypted_backup(out_path, request.password, files, meta)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    activity.log("backup_create", str(out_path))
    return {
        "ok": True,
        "path": str(out_path),
        "files": meta["files"],
        "format": "fdk",
        "warning": "Store the password safely. Wrong password cannot recover this file.",
    }


@app.post("/api/system/backup/restore")
def restore_encrypted_backup(request: BackupRestoreRequest) -> dict[str, Any]:
    """Restore a password-encrypted `.fdk` backup (or legacy integrity zip) into data_dir.

    Running sessions should be stopped first. Creates a pre-restore snapshot under backups/.
    """
    import hashlib
    import zipfile

    from backend.backup_crypto import read_encrypted_backup, write_encrypted_backup
    from backend.storage_util import atomic_write_text

    if registry.running_session_count() > 0:
        raise HTTPException(
            status_code=409,
            detail="stop all running sessions before restoring a backup",
        )

    path = Path(request.path).expanduser()
    if not path.is_absolute():
        path = (DATA_DIR / "backups" / path.name).resolve()
    else:
        path = path.resolve()
    backups_dir = (DATA_DIR / "backups").resolve()
    try:
        path.relative_to(DATA_DIR.resolve())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="backup path must be under data directory") from exc
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="backup file not found")

    files: dict[str, bytes] = {}
    meta: dict[str, Any] = {}
    try:
        meta, files = read_encrypted_backup(path, request.password)
    except ValueError as exc:
        msg = str(exc)
        if msg == "legacy_or_plain_zip" and path.suffix.lower() == ".zip":
            try:
                with zipfile.ZipFile(path, "r") as zf:
                    names = zf.namelist()
                    if "backup-meta.json" in names:
                        meta = json.loads(zf.read("backup-meta.json").decode("utf-8"))
                        stamp = str(meta.get("password_sha256") or "")
                        if stamp and hashlib.sha256(request.password.encode("utf-8")).hexdigest() != stamp:
                            raise HTTPException(status_code=400, detail="wrong password for legacy backup")
                    for name in names:
                        if name.endswith("/") or name == "backup-meta.json":
                            continue
                        files[name.replace("\\", "/")] = zf.read(name)
            except HTTPException:
                raise
            except Exception as zip_exc:
                raise HTTPException(status_code=400, detail=f"invalid legacy zip: {zip_exc}") from zip_exc
        elif "wrong password" in msg or "corrupted" in msg:
            raise HTTPException(status_code=400, detail="wrong password or corrupted backup") from exc
        else:
            raise HTTPException(status_code=400, detail=msg) from exc

    if not files:
        raise HTTPException(status_code=400, detail="backup contains no files")

    wanted = {n.strip() for n in (request.include or []) if n and n.strip()}
    restored: list[str] = []
    skipped: list[str] = []

    snap_path = None
    try:
        snap_files = _collect_backup_files(include_profiles_dirs=False)
        if snap_files:
            snap_path = backups_dir / f"pre-restore-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.fdk"
            write_encrypted_backup(
                snap_path,
                request.password,
                snap_files,
                {"app_version": APP_VERSION, "created_at": now_iso(), "note": "auto pre-restore snapshot"},
            )
    except Exception:
        snap_path = None

    for arcname, data in files.items():
        if wanted and arcname not in wanted and not any(arcname.startswith(w.rstrip("/") + "/") for w in wanted):
            skipped.append(arcname)
            continue
        target = _safe_restore_target(arcname)
        if target is None:
            skipped.append(arcname)
            continue
        if not request.overwrite and target.exists():
            skipped.append(arcname)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.suffix.lower() == ".json":
            try:
                text_out = data.decode("utf-8")
            except UnicodeDecodeError:
                text_out = data.decode("utf-8", errors="replace")
            atomic_write_text(target, text_out)
        else:
            tmp = target.with_name(f".{target.name}.{os.getpid()}.tmp")
            tmp.write_bytes(data)
            tmp.replace(target)
        restored.append(arcname)

    activity.log("backup_restore", f"path={path.name} restored={len(restored)} skipped={len(skipped)}")
    return {
        "ok": True,
        "path": str(path),
        "restored": restored,
        "skipped": skipped,
        "meta": meta,
        "pre_restore_snapshot": str(snap_path) if snap_path else None,
        "note": "JSON stores re-read on next API call; restart app if UI looks stale.",
    }


@app.post("/api/proxies/health-check")
def proxies_health_check_now() -> dict[str, Any]:
    result = proxy_health.run_once()
    activity.log("proxy_health_check", f"checked={result.get('checked')} failed={result.get('failed')}")
    return result


@app.get("/api/proxies/health-status")
def proxies_health_status() -> dict[str, Any]:
    return {"ok": True, **proxy_health.status()}


# --- Stop All Sessions ---
@app.post("/api/sessions/stop-all")
def stop_all_sessions() -> dict[str, Any]:
    sessions = registry.list("session")
    stopped = 0
    for s in sessions:
        if s["status"] == "running":
            try:
                registry.stop(s["id"])
                stopped += 1
            except Exception:
                pass
    activity.log("sessions_stop_all", f"stopped {stopped}")
    return {"stopped": stopped}


# --- Fingerprint Check ---
@app.get("/api/profiles/{profile_id}/fingerprint-check")
def fingerprint_check(profile_id: str) -> dict[str, Any]:
    """Static consistency + environment risk scoring (not a live anti-detect guarantee)."""
    try:
        profile = store.get(profile_id)
        profile = apply_proxy_pool_to_profile(profile)
    except KeyError:
        raise HTTPException(status_code=404, detail="profile not found") from None

    check_url = "https://browserleaks.com/javascript"
    has_proxy = bool((profile.proxy and profile.proxy.server) or profile.proxy_id)
    engine = normalize_engine_name(getattr(profile, "engine", None))
    checks = {
        "mode": profile.mode,
        "engine": engine,
        "chromium_backend": getattr(profile, "chromium_backend", None) or "",
        "chromium_channel": getattr(profile, "chromium_channel", None) or "",
        "os": profile.os,
        "headless": profile.headless,
        "proxy": (profile.proxy.server if profile.proxy and profile.proxy.server else "") or ("proxy_id:" + profile.proxy_id if profile.proxy_id else "none"),
        "geoip": profile.geoip,
        "screen": f"{profile.screen_width}x{profile.screen_height}" if profile.screen_width else "not set",
        "platform": profile.navigator_platform or "not set",
        "vendor": profile.navigator_vendor or "not set",
        "webgl": f"{profile.webgl_vendor} / {profile.webgl_renderer}" if profile.webgl_vendor else "not set",
        "canvas_noise": profile.canvas_noise,
        "audio_noise": profile.audio_noise,
        "block_webrtc": profile.block_webrtc,
        "webrtc_mode": profile.webrtc_mode,
        "timezone": profile.timezone or "not set",
        "locale": profile.locale or "not set",
        "persistent_context": profile.persistent_context,
        "humanize": profile.humanize,
        "font_pack": getattr(profile, "font_pack", None) or "",
        "media_devices": getattr(profile, "media_devices", None) or "default",
        "tags": list(profile.tags or [])[:16],
    }

    issues: list[str] = []
    if profile.headless:
        issues.append("Headless is on — payment/3DS pages often refuse this outright")
    if (profile.mode or "").lower() == "server":
        issues.append("Server mode is not suitable for interactive checkout")
    if not profile.navigator_platform and (profile.os or "auto") == "auto":
        issues.append("Platform/OS not pinned")
    if profile.screen_width and profile.screen_height:
        if profile.screen_width < 800 or profile.screen_height < 600:
            issues.append("Screen resolution too small for desktop checkout")
    if not profile.webgl_vendor and not profile.block_webgl:
        issues.append("WebGL vendor/renderer not set (will use Camoufox default)")
    if profile.block_webgl:
        issues.append("WebGL is blocked — many gateways expect GPU parameters")
    if profile.webrtc_mode == "default" and not profile.block_webrtc:
        issues.append("WebRTC not disabled — may leak real IP beside proxy")
    if has_proxy and not profile.geoip:
        issues.append("Proxy without geoip — timezone/locale may disagree with exit IP")
    if has_proxy and not (profile.timezone or "").strip():
        issues.append("Proxy without timezone")
    if has_proxy and not (profile.locale or "").strip():
        issues.append("Proxy without locale")
    if not has_proxy:
        issues.append("No proxy — exit IP is your real network")
    if profile.locale and profile.timezone:
        locale_tz_map = {
            "en-US": "America/",
            "en-GB": "Europe/London",
            "de-DE": "Europe/",
            "fr-FR": "Europe/",
            "ja-JP": "Asia/Tokyo",
            "zh-CN": "Asia/Shanghai",
            "zh-TW": "Asia/Taipei",
            "ko-KR": "Asia/Seoul",
        }
        for loc_prefix, tz_prefix in locale_tz_map.items():
            if profile.locale.startswith(loc_prefix) and profile.timezone.startswith(tz_prefix):
                break
        else:
            issues.append(
                f"Locale ({profile.locale}) and timezone ({profile.timezone}) may be inconsistent"
            )

    risks = environment_risks_for_profile(profile)
    high = sum(1 for r in risks if r.get("level") == "high")
    medium = sum(1 for r in risks if r.get("level") == "medium")
    score = 100 - (len(issues) * 12) - high * 8 - medium * 3
    return {
        "profile_id": profile_id,
        "checks": checks,
        "issues": issues,
        "environment_risks": risks,
        "score": max(0, min(100, score)),
        "check_url": check_url,
        "note": (
            "Static consistency only — not a payment / AI signup-pass guarantee. "
            "Camoufox is Firefox-based; many payment stacks score Chromium fingerprints differently."
        ),
    }
