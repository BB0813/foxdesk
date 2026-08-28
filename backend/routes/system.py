"""System routes: status, setup, settings, updates, tasks, channels,
diagnostics, resources, activity."""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.core import (
    APP_VERSION,
    DATA_DIR,
    GITHUB_REPO,
    activity,
    channel_store,
    now_iso,
    proxy_pool,
    registry,
    settings_store,
    store,
)
from backend.engine_meta import chromium_install_hint
from backend.engine_tools import (
    camoufox_command,
    camoufox_path_info,
    camoufox_version_info,
    cleanup_runtime_files,
    import_available,
    start_process,
)
from backend.models import (
    ChannelUpdateRequest,
    SetupStartRequest,
    SettingsUpdateRequest,
    TaskRequest,
    UpdateCheckRequest,
    UpdateInstallRequest,
)
from backend.profile_logic import detect_google_chrome_install, normalize_engine_name
from backend.wiring import proxy_health, setup_manager, update_manager

router = APIRouter()


@router.get("/api/system/ping")
def system_ping() -> dict[str, Any]:
    return {"ok": True, "app_version": APP_VERSION}


@router.get("/api/system")
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
        "api_token_header": "X-FoxDesk-Token",
        "proxy_pool_count": len(proxy_pool.all()),
        "profile_count": len(store.all()),
        "settings": settings_view,
        "update_mirror": settings_view.get("update_mirror"),
        "github_token_set": settings_view.get("github_token_set"),
    }


@router.get("/api/setup/status")
def setup_status() -> dict[str, Any]:
    return setup_manager.status()


@router.post("/api/setup/start")
def setup_start(request: SetupStartRequest | None = None) -> dict[str, Any]:
    req = request or SetupStartRequest()
    # Persist custom channel prefix if provided via channel store already.
    result = setup_manager.start(channel=req.channel or "github", auto=req.auto, force=req.force)
    activity.log("setup_start", f"channel={req.channel} force={req.force}")
    return result


@router.post("/api/setup/complete")
def setup_complete() -> dict[str, Any]:
    """Mark guided setup as completed even if user skips (not recommended)."""
    setup_manager.mark_completed()
    return {"ok": True, **setup_manager.status()}


@router.get("/api/settings")
def get_settings() -> dict[str, Any]:
    view = settings_store.get()
    return {
        "ok": True,
        **view,
        "proxy_health": proxy_health.status(),
        "running_sessions": registry.running_session_count(),
    }


@router.put("/api/settings")
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


@router.post("/api/system/diagnostics")
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
    from backend.core import store

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


@router.post("/api/system/health")
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


@router.post("/api/system/cleanup-runtime")
def system_cleanup_runtime(max_age_hours: float = 24.0) -> dict[str, Any]:
    result = cleanup_runtime_files(max_age_hours=max_age_hours)
    activity.log("runtime_cleanup", f"removed={result['removed']} kept={result['kept']}")
    return {"ok": True, **result}


@router.get("/api/system/updates")
def system_updates() -> dict[str, Any]:
    """Check GitHub Releases for a newer version (includes prereleases when current is beta)."""
    result = update_manager.check()
    return {
        "ok": result.get("status") != "failed",
        **result,
        "name": result.get("release_name"),
    }


@router.post("/api/system/updates/check")
def system_updates_check(request: UpdateCheckRequest | None = None) -> dict[str, Any]:
    req = request or UpdateCheckRequest()
    result = update_manager.check(
        include_prerelease=req.include_prerelease,
        force=bool(req.force),
    )
    activity.log("update_check", f"latest={result.get('latest')} status={result.get('status')}")
    return {"ok": result.get("status") != "failed", **result, "name": result.get("release_name")}


@router.get("/api/system/updates/status")
def system_updates_status() -> dict[str, Any]:
    return update_manager.status()


@router.post("/api/system/updates/download")
def system_updates_download() -> dict[str, Any]:
    result = update_manager.start_download()
    activity.log("update_download", f"status={result.get('status')} asset={result.get('asset_name')}")
    return {"ok": result.get("status") not in {"failed"}, **result}


@router.post("/api/system/updates/install")
def system_updates_install(request: UpdateInstallRequest | None = None) -> dict[str, Any]:
    req = request or UpdateInstallRequest()
    result = update_manager.install(exit_after=req.exit_after)
    activity.log("update_install", f"ok={result.get('ok')} path={result.get('local_path')}")
    if not result.get("ok"):
        raise HTTPException(status_code=409, detail=result.get("error") or "install failed")
    return result


def _validate_task_args(args: list[str]) -> list[str]:
    """Only conservative flag/value tokens reach pip / camoufox CLIs.

    Blocks URL and index/source injection (``--index-url http://evil`` and
    friends are equivalent to code execution via package install).
    """
    import re

    cleaned: list[str] = []
    blocked = {
        "--index-url", "-i", "--extra-index-url", "--editable", "-e",
        "--prefix", "--target", "-t", "--src", "--find-links", "-f",
        "--requirement", "-r", "--constraints", "-c", "--build-isolation",
    }
    for raw in args or []:
        arg = str(raw)
        if "://" in arg or arg.startswith(("http:", "https:", "ftp:")):
            raise HTTPException(status_code=400, detail=f"URLs are not allowed in task args: {arg[:60]}")
        if arg in blocked:
            raise HTTPException(status_code=400, detail=f"flag not allowed in task args: {arg}")
        if not re.fullmatch(r"[A-Za-z0-9._=\-]+", arg):
            raise HTTPException(status_code=400, detail=f"unsupported task arg: {arg[:60]}")
        cleaned.append(arg)
    return cleaned


@router.post("/api/tasks/{name}")
def start_task(name: str, request: TaskRequest | None = None) -> dict[str, Any]:
    allowed = {"install", "fetch", "test", "remove", "version", "path"}
    if name not in allowed:
        raise HTTPException(status_code=404, detail="unknown task")
    args = _validate_task_args(request.args if request else [])

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


@router.get("/api/tasks")
def list_tasks() -> list[dict[str, Any]]:
    return registry.list("task")


@router.get("/api/system/resources")
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


@router.get("/api/activity")
def list_activity(limit: int = 100) -> list[dict[str, str]]:
    return activity.list(limit)


def _validate_mirror_prefix(prefix: str) -> str:
    """Custom mirror prefixes must be an https:// URL with a plain host.

    The prefix is concatenated in front of GitHub download URLs and the result
    is executed (browser binaries) — http:// or credential-bearing URLs are
    rejected outright.
    """
    value = (prefix or "").strip()
    if not value:
        return value
    if "\\" in value or ".." in value:
        raise HTTPException(status_code=400, detail="invalid mirror prefix")
    try:
        from urllib.parse import urlparse

        parsed = urlparse(value if "://" in value else f"https://{value}")
    except Exception:
        raise HTTPException(status_code=400, detail="invalid mirror prefix") from None
    if parsed.scheme != "https" or not parsed.hostname:
        raise HTTPException(
            status_code=400,
            detail="mirror prefix must be an https:// URL (e.g. https://mirror.example.com/)",
        )
    if parsed.username or parsed.password:
        raise HTTPException(status_code=400, detail="mirror prefix must not contain credentials")
    # Normalize: caller may pass bare host.
    if "://" not in value:
        value = f"https://{value.rstrip('/')}/"
    return value


@router.get("/api/channels")
def list_channels() -> list[dict[str, Any]]:
    return channel_store.all()


@router.put("/api/channels")
def update_channel(request: ChannelUpdateRequest) -> dict[str, bool]:
    prefix = _validate_mirror_prefix(request.prefix)
    channel_store.update(request.id, prefix)
    return {"ok": True}


@router.post("/api/channels/{channel_id}/fetch")
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
