"""Engine tooling: availability probes, worker commands, process lifecycle."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any

from backend.core import (
    APP_EXECUTABLE,
    CREATE_NO_WINDOW,
    DATA_DIR,
    ROOT,
    RUNTIME_DIR,
    WORKER,
    WORKER_CHROMIUM,
    registry,
)
from backend.engine_meta import (
    chromium_install_hint,
    normalize_chromium_backend_name,
    normalize_engine_name,
)


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


def chromium_backend_available(name: str) -> bool:
    name = normalize_chromium_backend_name(name)
    if name == "auto":
        return import_available("playwright") or import_available("patchright")
    if name == "patchright":
        return import_available("patchright")
    return import_available("playwright")


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


def _wrap_runtime_proxy_secret(payload: dict[str, Any]) -> None:
    """DPAPI-seal the proxy password inside the worker runtime JSON.

    A crash otherwise leaves the plaintext credential on disk until the next
    cleanup sweep; sealed values are only readable by the same user. Workers
    unseal via storage_util.unprotect_secret (plaintext passes through).
    """
    proxy = payload.get("proxy")
    if isinstance(proxy, dict) and proxy.get("password"):
        try:
            from backend.storage_util import protect_secret

            proxy["password"] = protect_secret(str(proxy["password"]))
        except Exception:
            pass


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
):
    from backend.core import ManagedProcess

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
    with registry.lock:
        for item in registry.items.values():
            if item.runtime_path and item.process.poll() is None:
                base = Path(item.runtime_path).resolve()
                active_paths.add(str(base))
                # Protect the live control-channel sidecars as well.
                active_paths.add(str(base.with_suffix(".cmd.jsonl").resolve()))
                active_paths.add(str(base.with_suffix(".result.jsonl").resolve()))
    removed = 0
    kept = 0
    # Cover runtime JSON, .cmd.jsonl / .result.jsonl sidecars and stray
    # cookie exports alike (sidecars outlive crashes otherwise).
    candidates: list[Path] = []
    candidates.extend(RUNTIME_DIR.glob("*.json"))
    candidates.extend(RUNTIME_DIR.glob("*.cmd.jsonl"))
    candidates.extend(RUNTIME_DIR.glob("*.result.jsonl"))
    candidates.extend(RUNTIME_DIR.glob("*.ws"))
    candidates.extend(RUNTIME_DIR.glob("cookies-export-*.sqlite"))
    seen: set[Path] = set()
    for path in candidates:
        if path in seen:
            continue
        seen.add(path)
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
