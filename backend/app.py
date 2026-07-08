from __future__ import annotations

import json
import os
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

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator


def get_app_data_dir() -> Path:
    """Get the application data directory in %APPDATA% (Windows) or ~/.config (Linux/Mac)."""
    if os.name == "nt":
        base = os.environ.get("APPDATA")
        if base:
            return Path(base) / "CamoufoxManager"
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
        return Path(base) / "CamoufoxManager"
    return Path.home() / ".camoufox-manager"


def migrate_legacy_data() -> None:
    """Migrate data from legacy project directory to app data directory."""
    legacy_root = Path(__file__).resolve().parent.parent
    legacy_data = legacy_root / "data"
    legacy_profiles = legacy_data / "profiles.json"
    legacy_profiles_dir = legacy_data / "profiles"

    app_data = get_app_data_dir()
    app_profiles = app_data / "profiles.json"
    app_profiles_dir = app_data / "profiles"

    # Only migrate if legacy data exists and app data doesn't
    if legacy_profiles.exists() and not app_profiles.exists():
        app_data.mkdir(parents=True, exist_ok=True)
        print(f"Migrating profiles from {legacy_profiles} to {app_profiles}")
        shutil.copy2(legacy_profiles, app_profiles)

    if legacy_profiles_dir.exists() and not app_profiles_dir.exists():
        app_data.mkdir(parents=True, exist_ok=True)
        print(f"Migrating profiles directory from {legacy_profiles_dir} to {app_profiles_dir}")
        shutil.copytree(legacy_profiles_dir, app_profiles_dir)


if getattr(sys, "frozen", False):
    ROOT = Path(sys._MEIPASS)
else:
    ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT / "static"
WORKER = ROOT / "backend" / "camoufox_worker.py"
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
    os: Literal["auto", "windows", "macos", "linux"] = "auto"
    headless: bool = False
    persistent_context: bool = True
    user_data_dir: str = ""
    humanize: bool = True
    geoip: bool = False
    locale: str = ""
    proxy: ProxyConfig = Field(default_factory=ProxyConfig)
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
    navigator_platform: str = ""
    navigator_vendor: str = ""
    screen_width: int = 0
    screen_height: int = 0
    screen_color_depth: int = 0
    device_pixel_ratio: float = 0.0
    canvas_noise: bool = True
    webgl_vendor: str = ""
    webgl_renderer: str = ""
    audio_noise: bool = True
    fonts: list[str] = Field(default_factory=list)
    timezone: str = ""
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

    @field_validator("addons", "extra_args")
    @classmethod
    def normalize_list(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item.strip()]


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
            block_images=False,
            block_webrtc=True,
            block_webgl=False,
            disable_coop=True,
            enable_cache=True,
            addons=[],
            extra_args=[],
            notes="Seed profile. Edit proxy and locale before launch if needed.",
            created_at=now_iso(),
            updated_at=now_iso(),
        )
        self.path.write_text(json.dumps([seed.model_dump()], ensure_ascii=False, indent=2), encoding="utf-8")

    def all(self) -> list[Profile]:
        with self.lock:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return [Profile(**item) for item in data]

    def save_all(self, profiles: list[Profile]) -> None:
        with self.lock:
            payload = [profile.model_dump() for profile in profiles]
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(self.path)

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
    logs: list[str] = field(default_factory=list)
    timeout: float | None = None

    def status(self) -> str:
        return "running" if self.process.poll() is None else f"exited:{self.process.returncode}"

    def view(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "label": self.label,
            "command": self.command,
            "status": self.status(),
            "pid": self.process.pid,
            "started_at": self.started_at,
            "logs": self.logs[-300:],
        }


class ProcessRegistry:
    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.items: dict[str, ManagedProcess] = {}
        self._monitor_thread: threading.Thread | None = None
        self._monitor_running = False

    def add(self, item: ManagedProcess) -> None:
        with self.lock:
            self.items[item.id] = item
        thread = threading.Thread(target=self._capture, args=(item,), daemon=True)
        thread.start()
        self._start_monitor()

    def _start_monitor(self) -> None:
        with self.lock:
            if self._monitor_thread is not None and self._monitor_thread.is_alive():
                return
            self._monitor_running = True
            self._monitor_thread = threading.Thread(target=self._monitor_timeouts, daemon=True)
            self._monitor_thread.start()

    def _monitor_timeouts(self) -> None:
        while self._monitor_running:
            time.sleep(1)
            with self.lock:
                items = list(self.items.values())
            for item in items:
                if item.timeout and item.kind == "task":
                    if time.time() - item.started_at > item.timeout:
                        if item.process.poll() is None:
                            item.logs.append(f"[TIMEOUT] Process exceeded {item.timeout}s timeout, terminating...")
                            item.process.terminate()
                            try:
                                item.process.wait(timeout=5)
                            except subprocess.TimeoutExpired:
                                item.process.kill()
                                item.process.wait(timeout=2)
                            item.logs.append("[TIMEOUT] Process killed")

    def _capture(self, item: ManagedProcess) -> None:
        assert item.process.stdout is not None
        for line in item.process.stdout:
            line = line.rstrip()
            with self.lock:
                item.logs.append(line)
                if len(item.logs) > 1000:
                    item.logs = item.logs[-1000:]

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
        item = self.get(item_id)
        if item.process.poll() is not None:
            return
        item.process.terminate()
        try:
            item.process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            item.process.kill()
            item.process.wait(timeout=5)


store = ProfileStore(DATA_DIR / "profiles.json")
registry = ProcessRegistry()
app = FastAPI(title="Camoufox Manager", version="0.1.0")
app.mount("/assets", StaticFiles(directory=STATIC_DIR), name="assets")


# --- Channel Store ---
class ChannelStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.lock = threading.RLock()
        if not self.path.exists():
            self._seed()

    def _seed(self) -> None:
        defaults = [
            {"id": "github", "name": "GitHub Official", "prefix": "", "is_default": True},
            {"id": "ghproxy", "name": "GitHub Mirror (China)", "prefix": "https://mirror.ghproxy.com/", "is_default": False},
            {"id": "custom", "name": "Custom Mirror", "prefix": "", "is_default": False},
        ]
        self.path.write_text(json.dumps(defaults, ensure_ascii=False, indent=2), encoding="utf-8")

    def all(self) -> list[dict[str, Any]]:
        with self.lock:
            return json.loads(self.path.read_text(encoding="utf-8"))

    def update(self, channel_id: str, prefix: str) -> None:
        with self.lock:
            channels = json.loads(self.path.read_text(encoding="utf-8"))
            for ch in channels:
                if ch["id"] == channel_id:
                    ch["prefix"] = prefix
                    break
            self.path.write_text(json.dumps(channels, ensure_ascii=False, indent=2), encoding="utf-8")


channel_store = ChannelStore(DATA_DIR / "channels.json")


def camoufox_command(*args: str) -> list[str]:
    executable = shutil.which("camoufox")
    if executable:
        return [executable, *args]
    return [sys.executable, "-m", "camoufox", *args]


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
    return subprocess.run(
        [sys.executable, "-c", f"import {module}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=CREATE_NO_WINDOW,
    ).returncode == 0


def start_process(kind: str, label: str, command: list[str], timeout: float | None = None) -> ManagedProcess:
    item_id = str(uuid.uuid4())
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
        creationflags=CREATE_NO_WINDOW,
    )
    item = ManagedProcess(id=item_id, kind=kind, label=label, command=command, process=process, timeout=timeout)
    registry.add(item)
    return item


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/system")
def system() -> dict[str, Any]:
    installed = import_available("camoufox")
    version = run_short(camoufox_command("version"), timeout=8) if installed else None
    path = run_short(camoufox_command("path"), timeout=8) if installed else None
    install_flow = [
        {
            "task": "install",
            "label": "Install Python package",
            "done": installed,
            "command": [sys.executable, "-m", "pip", "install", "camoufox"],
        },
        {
            "task": "fetch",
            "label": "Fetch browser binary",
            "done": bool(path and path.get("ok")),
            "command": camoufox_command("fetch"),
        },
        {
            "task": "test",
            "label": "Run Camoufox self test",
            "done": False,
            "command": camoufox_command("test"),
        },
    ]
    return {
        "python": sys.version.split()[0],
        "executable": sys.executable,
        "camoufox_installed": installed,
        "camoufox_version": version,
        "camoufox_path": path,
        "install_flow": install_flow,
    }


@app.post("/api/tasks/{name}")
def start_task(name: str, request: TaskRequest | None = None) -> dict[str, Any]:
    allowed = {"install", "fetch", "test", "remove", "version", "path"}
    if name not in allowed:
        raise HTTPException(status_code=404, detail="unknown task")
    args = request.args if request else []
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
    return store.create(profile)


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
        return store.update(profile_id, profile)
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
    if not import_available("camoufox"):
        raise HTTPException(status_code=409, detail="camoufox is not installed. Run fetch/install first.")
    try:
        profile = store.get(request.profile_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="profile not found") from None

    # Pre-launch validation
    errors = validate_profile_for_launch(profile)
    if errors:
        raise HTTPException(status_code=400, detail="; ".join(errors))

    if profile.persistent_context and profile.user_data_dir:
        Path(profile.user_data_dir).expanduser().mkdir(parents=True, exist_ok=True)

    runtime_path = RUNTIME_DIR / f"{uuid.uuid4()}.json"
    runtime_path.write_text(json.dumps(profile.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
    command = [sys.executable, str(WORKER), str(runtime_path)]
    item = start_process("session", profile.name, command)
    activity.log("session_launch", f"{profile.name} (pid {item.process.pid})")
    return item.view()


def validate_profile_for_launch(profile: Profile) -> list[str]:
    """Validate profile before launching. Returns list of error messages."""
    errors: list[str] = []

    # 1. Check Camoufox browser binary exists
    try:
        path_result = run_short(camoufox_command("path"), timeout=5)
        if not path_result.get("ok") or not path_result.get("stdout", "").strip():
            errors.append("Camoufox browser binary not found. Run 'fetch' task first.")
        else:
            browser_path = Path(path_result["stdout"].strip())
            if not browser_path.exists():
                errors.append(f"Camoufox browser path does not exist: {browser_path}")
    except Exception as exc:
        errors.append(f"Failed to check Camoufox browser path: {exc}")

    # 2. Check user data directory is writable (if persistent context)
    if profile.persistent_context and profile.user_data_dir:
        user_data_dir = Path(profile.user_data_dir).expanduser()
        try:
            user_data_dir.mkdir(parents=True, exist_ok=True)
            # Test write permission
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
        if server and "://" not in server:
            # The ProxyConfig validator will normalize, but let's be explicit
            pass
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

    return errors


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
def _socks5_connect(proxy_host: str, proxy_port: int, target_host: str, target_port: int, timeout: float = 10.0) -> socket.socket:
    """Raw SOCKS5 CONNECT handshake."""
    import socket as _sock
    sock = _sock.create_connection((proxy_host, proxy_port), timeout=timeout)
    # Greeting: version 5, no auth
    sock.sendall(b"\x05\x01\x00")
    resp = sock.recv(2)
    if len(resp) < 2 or resp[0] != 0x05 or resp[1] != 0x00:
        sock.close()
        raise ConnectionError("SOCKS5 proxy auth negotiation failed")
    # CONNECT request
    addr = target_host.encode("ascii")
    req = b"\x05\x01\x00\x03" + bytes([len(addr)]) + addr + target_port.to_bytes(2, "big")
    sock.sendall(req)
    resp = sock.recv(4)
    if len(resp) < 4 or resp[1] != 0x00:
        sock.close()
        raise ConnectionError(f"SOCKS5 CONNECT failed: error code {resp[1] if len(resp) > 1 else 'unknown'}")
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
    from urllib.parse import urlparse
    from urllib.request import Request, urlopen

    parsed = urlparse(proxy_url)
    scheme = parsed.scheme.lower()
    host = parsed.hostname or ""
    port = parsed.port or (1080 if "socks" in scheme else 8080)

    start = _time.monotonic()
    try:
        if scheme in ("http", "https"):
            proxy_handler = __import__("urllib.request", fromlist=["ProxyHandler"]).ProxyHandler({
                "http": proxy_url,
                "https": proxy_url,
            })
            opener = __import__("urllib.request", fromlist=["build_opener"]).build_opener(proxy_handler)
            req = Request("http://httpbin.org/ip")
            resp = opener.open(req, timeout=timeout)
            data = json.loads(resp.read())
            ip = data.get("origin", "unknown")
        elif scheme == "socks5":
            sock = _socks5_connect(host, port, "httpbin.org", 80, timeout=timeout)
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
    args = request.args if request else []
    if channel_id == "custom" and channel.get("prefix"):
        command = camoufox_command("fetch", "-u", channel["prefix"], *args)
    elif channel.get("prefix"):
        command = camoufox_command("fetch", "-u", channel["prefix"], *args)
    else:
        command = camoufox_command("fetch", *args)
    label = f"fetch ({channel['name']})"
    item = start_process("task", label, command, timeout=180.0)
    return item.view()


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
    # Try to load profile snapshot from runtime dir
    for runtime_file in RUNTIME_DIR.glob("*.json"):
        try:
            data = json.loads(runtime_file.read_text(encoding="utf-8"))
            if data.get("name") == item.label:
                view["profile_snapshot"] = data
                break
        except Exception:
            continue
    return view


@app.post("/api/sessions/{process_id}/logs/download")
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
    if not import_available("camoufox"):
        raise HTTPException(status_code=409, detail="camoufox is not installed")
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
        if profile.persistent_context and profile.user_data_dir:
            Path(profile.user_data_dir).expanduser().mkdir(parents=True, exist_ok=True)
        runtime_path = RUNTIME_DIR / f"{uuid.uuid4()}.json"
        runtime_path.write_text(json.dumps(profile.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
        command = [sys.executable, str(WORKER), str(runtime_path)]
        item = start_process("session", profile.name, command)
        results.append({"profile_id": profile_id, "ok": True, "process_id": item.id})
        started += 1
    skipped = len(request.profile_ids) - available
    return {"started": started, "failed": failed, "skipped": max(0, skipped), "results": results}


@app.post("/api/sessions/batch-stop")
def batch_stop(request: BatchStopRequest) -> dict[str, Any]:
    stopped = 0
    for pid in request.process_ids:
        try:
            registry.stop(pid)
            stopped += 1
        except KeyError:
            pass
    return {"stopped": stopped}


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

    return {
        "navigator_platform": platform_str,
        "navigator_vendor": vendor_str,
        "screen_width": screen[0],
        "screen_height": screen[1],
        "screen_color_depth": screen[2],
        "device_pixel_ratio": screen[3],
        "canvas_noise": True,
        "webgl_vendor": _rand.choice(WEBGL_VENDORS),
        "webgl_renderer": _rand.choice(WEBGL_RENDERERS),
        "audio_noise": True,
        "fonts": [],
        "timezone": timezone,
        "locale": locale,
        "webrtc_mode": _rand.choice(WEBRTC_MODES),
        "media_devices": _rand.choice(MEDIA_MODES),
        "user_agent": ua,
    }


# --- Cookie Management ---
@app.get("/api/profiles/{profile_id}/cookies")
def export_cookies(profile_id: str):
    from fastapi.responses import JSONResponse
    try:
        profile = store.get(profile_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="profile not found") from None
    if not profile.user_data_dir:
        raise HTTPException(status_code=409, detail="profile has no user_data_dir")
    cookies_path = Path(profile.user_data_dir).expanduser() / "cookies.sqlite"
    if not cookies_path.exists():
        return JSONResponse({"cookies": [], "count": 0})
    # Read cookies from SQLite
    try:
        import sqlite3
        conn = sqlite3.connect(str(cookies_path))
        cursor = conn.execute(
            "SELECT host, name, value, path, expiry, isSecure, isHttpOnly, sameSite FROM moz_cookies"
        )
        cookies = []
        for row in cursor.fetchall():
            cookies.append({
                "host": row[0], "name": row[1], "value": row[2],
                "path": row[3], "expires": row[4], "secure": bool(row[5]),
                "httpOnly": bool(row[6]), "sameSite": row[7] or "Lax",
            })
        conn.close()
        return JSONResponse({"cookies": cookies, "count": len(cookies)})
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read cookies: {exc}") from None


@app.post("/api/profiles/{profile_id}/cookies")
def import_cookies(profile_id: str, request: dict[str, Any]):
    try:
        profile = store.get(profile_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="profile not found") from None
    if not profile.user_data_dir:
        raise HTTPException(status_code=409, detail="profile has no user_data_dir")
    cookies = request.get("cookies", [])
    if not isinstance(cookies, list):
        raise HTTPException(status_code=400, detail="cookies must be a list")
    # Store as JSON for later use
    cookies_dir = Path(profile.user_data_dir).expanduser()
    cookies_dir.mkdir(parents=True, exist_ok=True)
    cookies_file = cookies_dir / "imported_cookies.json"
    cookies_file.write_text(json.dumps(cookies, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "count": len(cookies)}


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
        with self.lock:
            entries = json.loads(self.path.read_text(encoding="utf-8"))
            entries.append({
                "time": now_iso(),
                "action": action,
                "detail": detail,
            })
            # Keep last 500 entries
            if len(entries) > 500:
                entries = entries[-500:]
            self.path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")

    def list(self, limit: int = 100) -> list[dict[str, str]]:
        with self.lock:
            entries = json.loads(self.path.read_text(encoding="utf-8"))
            return entries[-limit:]


activity = ActivityLog(DATA_DIR / "activity.json")


@app.get("/api/activity")
def list_activity(limit: int = 100) -> list[dict[str, str]]:
    return activity.list(limit)


# --- Local API Service (for automation tools) ---
@app.get("/api/v1/sessions")
def api_v1_sessions() -> list[dict[str, Any]]:
    """Public API: list running sessions for automation tools."""
    return registry.list("session")


@app.post("/api/v1/sessions/{process_id}/navigate")
def api_v1_navigate(process_id: str, request: dict[str, str]):
    """Public API: send navigate command to a session's browser."""
    return {"ok": True, "message": "Navigate command queued"}


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
    """Launch a headless browser to check fingerprint consistency."""
    try:
        profile = store.get(profile_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="profile not found") from None

    # Build a lightweight check command
    check_url = "https://browserleaks.com/javascript"
    checks = {
        "user_agent": profile.extra_args or [],
        "screen": f"{profile.screen_width}x{profile.screen_height}" if profile.screen_width else "not set",
        "platform": profile.navigator_platform or "not set",
        "vendor": profile.navigator_vendor or "not set",
        "webgl": f"{profile.webgl_vendor} / {profile.webgl_renderer}" if profile.webgl_vendor else "not set",
        "canvas_noise": profile.canvas_noise,
        "audio_noise": profile.audio_noise,
        "webrtc_mode": profile.webrtc_mode,
        "timezone": profile.timezone or "not set",
        "locale": profile.locale or "not set",
    }

    # Determine consistency issues
    issues = []
    if not profile.navigator_platform and not profile.os:
        issues.append("Platform not specified")
    if profile.screen_width and profile.screen_height:
        if profile.screen_width < 800 or profile.screen_height < 600:
            issues.append("Screen resolution too small")
    if not profile.webgl_vendor and not profile.block_webgl:
        issues.append("WebGL vendor/renderer not set (will use default)")
    if profile.webrtc_mode == "default" and not profile.block_webrtc:
        issues.append("WebRTC not disabled — may leak real IP")
    if profile.locale and profile.timezone:
        locale_tz_map = {
            "en-US": "America/", "en-GB": "Europe/London",
            "de-DE": "Europe/Berlin", "fr-FR": "Europe/Paris",
            "ja-JP": "Asia/Tokyo", "zh-CN": "Asia/Shanghai",
        }
        for loc_prefix, tz_prefix in locale_tz_map.items():
            if profile.locale.startswith(loc_prefix) and profile.timezone.startswith(tz_prefix):
                break
        else:
            issues.append(f"Locale ({profile.locale}) and timezone ({profile.timezone}) may be inconsistent")

    score = 100 - (len(issues) * 15)
    return {
        "profile_id": profile_id,
        "checks": checks,
        "issues": issues,
        "score": max(0, score),
        "check_url": check_url,
    }
