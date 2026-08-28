"""Session routes: launch, batch, live control commands, server endpoints."""
from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from backend.core import (
    RUNTIME_DIR,
    activity,
    registry,
    settings_store,
    store,
)
from backend.engine_meta import (
    chromium_install_hint,
    humanize_chromium_launch_error,
    normalize_engine_name,
)
from backend.engine_tools import (
    _wrap_runtime_proxy_secret,
    cleanup_runtime_files,
    import_available,
    resolve_chromium_backend,
    start_process,
    worker_command,
)
from backend.models import (
    BatchLaunchRequest,
    BatchStopRequest,
    EvaluateRequest,
    LaunchRequest,
    NavigateRequest,
    ScreenshotRequest,
)
from backend.profile_logic import (
    apply_proxy_pool_to_profile,
    environment_risks_for_profile,
    normalize_profile_paths,
    validate_profile_for_launch,
)
from backend.session_control import send_worker_command
from backend.storage_util import atomic_write_json

router = APIRouter()


@router.post("/api/sessions")
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
    _wrap_runtime_proxy_secret(payload)
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


@router.get("/api/sessions")
def list_sessions() -> list[dict[str, Any]]:
    return registry.list("session")


@router.post("/api/processes/{process_id}/stop")
def stop_process(process_id: str) -> dict[str, Any]:
    try:
        registry.stop(process_id)
        return registry.get(process_id).view()
    except KeyError:
        raise HTTPException(status_code=404, detail="process not found") from None


# --- Session Detail ---
@router.get("/api/sessions/{process_id}")
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


@router.api_route("/api/sessions/{process_id}/logs/download", methods=["GET", "POST"])
def download_session_logs(process_id: str):
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


@router.post("/api/sessions/batch")
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
        _wrap_runtime_proxy_secret(payload)
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


@router.post("/api/sessions/batch-stop")
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
@router.get("/api/v1/sessions")
def api_v1_sessions() -> list[dict[str, Any]]:
    """Public API: list running sessions for automation tools."""
    return registry.list("session")


@router.post("/api/v1/sessions/{process_id}/navigate")
def api_v1_navigate(process_id: str, request: NavigateRequest) -> dict[str, Any]:
    """Live-navigate a running browser-mode session to a URL."""
    return _session_command(process_id, "navigate", {"url": request.url})


@router.post("/api/sessions/{process_id}/navigate")
def session_navigate(process_id: str, request: NavigateRequest) -> dict[str, Any]:
    result = _session_command(process_id, "navigate", {"url": request.url})
    activity.log("session_navigate", f"{process_id} -> {request.url}")
    return result


@router.post("/api/sessions/{process_id}/fingerprint")
def session_fingerprint_probe(process_id: str) -> dict[str, Any]:
    """Probe live fingerprint values from a running browser session."""
    result = _session_command(process_id, "fingerprint", timeout=60.0)
    activity.log("session_fingerprint", process_id)
    return result


@router.post("/api/sessions/{process_id}/screenshot")
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


@router.post("/api/sessions/{process_id}/evaluate")
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


@router.post("/api/sessions/{process_id}/endpoint")
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


# --- Stop All Sessions ---
@router.post("/api/sessions/stop-all")
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
