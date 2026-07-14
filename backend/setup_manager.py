from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


@dataclass
class SetupStep:
    id: str
    label: str
    status: str = "pending"  # pending | running | done | skipped | failed
    detail: str = ""


@dataclass
class SetupState:
    status: str = "idle"  # idle | running | done | failed
    current_step: str = ""
    steps: list[SetupStep] = field(default_factory=list)
    logs: list[str] = field(default_factory=list)
    error: str | None = None
    started_at: float | None = None
    finished_at: float | None = None
    channel: str = "github"
    auto: bool = True

    def view(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "current_step": self.current_step,
            "steps": [
                {
                    "id": s.id,
                    "label": s.label,
                    "status": s.status,
                    "detail": s.detail,
                }
                for s in self.steps
            ],
            "logs": self.logs[-200:],
            "error": self.error,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "channel": self.channel,
            "auto": self.auto,
            "progress": self._progress(),
        }

    def _progress(self) -> int:
        if not self.steps:
            return 0
        weight = {"done": 1, "skipped": 1, "running": 0.5, "failed": 0, "pending": 0}
        total = sum(weight.get(s.status, 0) for s in self.steps)
        return int(round(100 * total / len(self.steps)))


class SetupManager:
    """One-shot guided environment installer for first run."""

    def __init__(
        self,
        *,
        is_frozen: bool,
        executable: Path | str,
        root: Path,
        create_no_window: int,
        camoufox_command: Callable[..., list[str]],
        import_available: Callable[[str], bool],
        channel_prefix: Callable[[str], str | None] | None = None,
        marker_path: Path | None = None,
    ) -> None:
        self.is_frozen = is_frozen
        self.executable = Path(executable)
        self.root = Path(root)
        self.create_no_window = create_no_window
        self.camoufox_command = camoufox_command
        self.import_available = import_available
        self.channel_prefix = channel_prefix or (lambda _cid: None)
        self.marker_path = marker_path
        self.lock = threading.RLock()
        self.state = SetupState()
        self._thread: threading.Thread | None = None

    def status(self) -> dict[str, Any]:
        with self.lock:
            data = self.state.view()
        data["needs_setup"] = self.needs_setup()
        data["setup_completed_marker"] = self._marker_done()
        return data

    def needs_setup(self) -> bool:
        if not self.import_available("camoufox"):
            return True
        ready, _ = self._browser_ready()
        return not ready

    def _marker_done(self) -> bool:
        if not self.marker_path:
            return False
        return self.marker_path.exists()

    def mark_completed(self) -> None:
        if not self.marker_path:
            return
        try:
            self.marker_path.parent.mkdir(parents=True, exist_ok=True)
            self.marker_path.write_text(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), encoding="utf-8")
        except OSError:
            pass

    def start(self, *, channel: str = "github", auto: bool = True, force: bool = False) -> dict[str, Any]:
        with self.lock:
            if self.state.status == "running":
                return self.state.view()
            if not force and not self.needs_setup() and self._marker_done():
                self.state = SetupState(status="done", channel=channel, auto=auto)
                self.state.steps = [
                    SetupStep("check", "Environment check", "done", "already ready"),
                    SetupStep("package", "Install Camoufox package", "skipped", "already installed"),
                    SetupStep("fetch", "Download browser files", "skipped", "already present"),
                    SetupStep("verify", "Verify installation", "done", "ok"),
                ]
                self.state.finished_at = time.time()
                return self.state.view()

            self.state = SetupState(
                status="running",
                channel=channel or "github",
                auto=auto,
                started_at=time.time(),
            )
            self.state.steps = [
                SetupStep("check", "Environment check"),
                SetupStep("package", "Install Camoufox package"),
                SetupStep("fetch", "Download browser files"),
                SetupStep("verify", "Verify installation"),
            ]
            self._thread = threading.Thread(target=self._run_pipeline, daemon=True)
            self._thread.start()
            return self.state.view()

    def _log(self, line: str) -> None:
        with self.lock:
            self.state.logs.append(line)
            if len(self.state.logs) > 500:
                self.state.logs = self.state.logs[-500:]

    def _set_step(self, step_id: str, status: str, detail: str = "") -> None:
        with self.lock:
            self.state.current_step = step_id
            for step in self.state.steps:
                if step.id == step_id:
                    step.status = status
                    if detail:
                        step.detail = detail
                    break

    def _fail_current(self, exc: Exception | str) -> None:
        message = str(exc)
        with self.lock:
            self.state.status = "failed"
            self.state.error = message
            self.state.finished_at = time.time()
            for step in self.state.steps:
                if step.id == self.state.current_step and step.status == "running":
                    step.status = "failed"
                    step.detail = message
                    break

    def _run(self, command: list[str], timeout: int = 300) -> dict[str, Any]:
        self._log(f"$ {' '.join(command)}")
        try:
            completed = subprocess.run(
                command,
                cwd=str(self.root),
                text=True,
                capture_output=True,
                timeout=timeout,
                creationflags=self.create_no_window,
            )
            out = (completed.stdout or "").strip()
            err = (completed.stderr or "").strip()
            if out:
                for line in out.splitlines()[-40:]:
                    self._log(line)
            if err:
                for line in err.splitlines()[-40:]:
                    self._log(line)
            return {
                "ok": completed.returncode == 0,
                "returncode": completed.returncode,
                "stdout": out,
                "stderr": err,
            }
        except subprocess.TimeoutExpired as exc:
            self._log(f"[timeout] exceeded {timeout}s")
            return {"ok": False, "returncode": None, "stdout": "", "stderr": str(exc)}
        except Exception as exc:
            self._log(f"[error] {exc}")
            return {"ok": False, "returncode": None, "stdout": "", "stderr": str(exc)}

    def _run_pipeline(self) -> None:
        try:
            self._step_check()
            self._step_package()
            self._step_fetch()
            self._step_verify()
            with self.lock:
                self.state.status = "done"
                self.state.error = None
                self.state.finished_at = time.time()
            self.mark_completed()
            self._log("[done] setup completed")
        except Exception as exc:
            self._fail_current(exc)
            self._log(f"[failed] {exc}")

    def _step_check(self) -> None:
        self._set_step("check", "running")
        frozen = self.is_frozen
        detail = f"frozen={frozen} python={sys.version.split()[0]}"
        self._log(detail)
        self._set_step("check", "done", detail)

    def _probe_camoufox_bundle(self) -> tuple[bool, str]:
        """Verify camoufox + fingerprint datapoints are importable."""
        try:
            import camoufox  # noqa: F401
            import apify_fingerprint_datapoints
            from camoufox import fingerprints  # noqa: F401
            from camoufox.pkgman import INSTALL_DIR  # noqa: F401

            # Ensure zip datapoints exist on disk (common frozen packaging miss).
            data_dir = Path(apify_fingerprint_datapoints.__file__).resolve().parent / "data"
            required = [
                "input-network-definition.zip",
                "header-network-definition.zip",
                "fingerprint-network-definition.zip",
            ]
            missing = [name for name in required if not (data_dir / name).exists()]
            if missing:
                return False, f"missing datapoints: {', '.join(missing)} under {data_dir}"
            return True, f"ok ({data_dir})"
        except Exception as exc:
            return False, str(exc)

    def _step_package(self) -> None:
        self._set_step("package", "running")
        if self.is_frozen:
            # Bundled app must ship camoufox; pip against FoxDesk.exe is invalid.
            ok, detail = self._probe_camoufox_bundle()
            if ok:
                self._set_step("package", "skipped", "bundled in app")
                self._log(f"package: camoufox bundled ({detail})")
                return
            raise RuntimeError(
                "安装包缺少 Camoufox/指纹数据组件。请卸载旧版后安装最新 FoxDesk，"
                "或改用源码模式运行。"
                f" ({detail})"
            )

        ok, detail = self._probe_camoufox_bundle()
        if ok:
            self._set_step("package", "skipped", "already installed")
            self._log(f"package: already installed ({detail})")
            return

        cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "camoufox"]
        result = self._run(cmd, timeout=300)
        ok, detail = self._probe_camoufox_bundle()
        if not result.get("ok") or not ok:
            raise RuntimeError(result.get("stderr") or detail or "pip install camoufox failed")
        self._set_step("package", "done", "installed")

    def _mirror_prefix(self, channel: str) -> str | None:
        prefix = self.channel_prefix(channel)
        if prefix:
            return prefix.rstrip("/") + "/"
        if channel == "ghproxy":
            return "https://mirror.ghproxy.com/"
        return None

    def _with_github_mirror(self, prefix: str | None):
        """Temporarily rewrite GitHub URLs for restricted networks."""
        if not prefix:
            class _Noop:
                def __enter__(self_inner):
                    return None

                def __exit__(self_inner, *args):
                    return False

            return _Noop()

        class _Mirror:
            def __enter__(self_inner):
                import requests
                from camoufox import pkgman

                self_inner._requests_get = requests.get
                self_inner._webdl = getattr(pkgman, "webdl", None)

                def rewrite(url: str) -> str:
                    if not isinstance(url, str):
                        return url
                    if url.startswith(prefix):
                        return url
                    if "github.com" in url or "githubusercontent.com" in url:
                        return prefix + url
                    return url

                def get_wrapped(url, *args, **kwargs):
                    return self_inner._requests_get(rewrite(url), *args, **kwargs)

                requests.get = get_wrapped  # type: ignore[assignment]
                if self_inner._webdl is not None:
                    def webdl_wrapped(url, *args, **kwargs):
                        return self_inner._webdl(rewrite(url), *args, **kwargs)

                    pkgman.webdl = webdl_wrapped  # type: ignore[assignment]
                return rewrite

            def __exit__(self_inner, *args):
                import requests
                from camoufox import pkgman

                requests.get = self_inner._requests_get  # type: ignore[assignment]
                if self_inner._webdl is not None:
                    pkgman.webdl = self_inner._webdl  # type: ignore[assignment]
                return False

        return _Mirror()

    def _browser_ready(self) -> tuple[bool, str]:
        # Prefer in-process path checks — works in frozen builds where
        # `FoxDesk.exe -m camoufox` is not a valid Python CLI.
        if self.import_available("camoufox") or self.is_frozen:
            try:
                from camoufox.pkgman import INSTALL_DIR, LAUNCH_FILE, OS_NAME, Version

                if not INSTALL_DIR.exists() or not any(INSTALL_DIR.iterdir()):
                    return False, f"not installed ({INSTALL_DIR})"
                try:
                    ver = Version.from_path(INSTALL_DIR)
                    if not ver.is_supported():
                        return False, f"unsupported version {ver.full_string}"
                    ver_text = ver.full_string
                except Exception as exc:
                    return False, f"version check failed: {exc}"
                launch = INSTALL_DIR / LAUNCH_FILE[OS_NAME]
                if OS_NAME == "mac":
                    launch = INSTALL_DIR / "Camoufox.app" / "Contents" / "MacOS" / "camoufox"
                if not Path(launch).exists():
                    return False, f"binary missing: {launch}"
                return True, f"{INSTALL_DIR} (v{ver_text})"
            except Exception as exc:
                self._log(f"in-process path check failed: {exc}")

        if not self.import_available("camoufox"):
            return False, "camoufox import failed"
        if self.is_frozen:
            return False, "camoufox binary not found"
        result = self._run(self.camoufox_command("path"), timeout=20)
        path_text = (result.get("stdout") or "").strip()
        # click may colorize; take last non-empty token-like line
        if path_text:
            path_text = path_text.splitlines()[-1].strip()
        if not path_text:
            return False, result.get("stderr") or "empty path"
        if not Path(path_text).exists():
            return False, f"path missing: {path_text}"
        return True, path_text

    def _fetch_inprocess(self, channel: str) -> None:
        prefix = self._mirror_prefix(channel)
        if prefix:
            self._log(f"using download mirror: {prefix}")
        with self._with_github_mirror(prefix):
            from camoufox.__main__ import CamoufoxUpdate
            from camoufox.addons import DefaultAddons, maybe_download_addons
            from camoufox.locale import ALLOW_GEOIP, download_mmdb

            self._log("fetch: CamoufoxUpdate().update()")
            CamoufoxUpdate().update()
            if ALLOW_GEOIP:
                self._log("fetch: download GeoIP mmdb")
                try:
                    download_mmdb()
                except Exception as exc:
                    self._log(f"geoip download skipped: {exc}")
            try:
                maybe_download_addons(list(DefaultAddons))
            except Exception as exc:
                self._log(f"addons download skipped: {exc}")

    def _fetch_commands(self, channel: str) -> list[list[str]]:
        commands: list[list[str]] = []
        # Official CLI has no stable -u mirror flag across versions; keep simple fetch.
        commands.append(self.camoufox_command("fetch"))
        return commands

    def _step_fetch(self) -> None:
        self._set_step("fetch", "running")
        ready, detail = self._browser_ready()
        if ready:
            self._set_step("fetch", "skipped", detail)
            self._log(f"fetch: browser already present at {detail}")
            return

        channel = self.state.channel or "github"
        last_error = "fetch failed"

        # Frozen / preferred path: call camoufox APIs in-process.
        if self.is_frozen or self.import_available("camoufox"):
            try:
                self._fetch_inprocess(channel)
                ready, detail = self._browser_ready()
                if ready:
                    self._set_step("fetch", "done", detail)
                    return
                last_error = detail or last_error
            except Exception as exc:
                last_error = str(exc)
                self._log(f"in-process fetch failed: {exc}")

        # Source mode fallback: subprocess CLI (and retry with alternate channel).
        if not self.is_frozen:
            for cmd in self._fetch_commands(channel):
                self._log(f"trying fetch via: {' '.join(cmd)}")
                result = self._run(cmd, timeout=600)
                ready, detail = self._browser_ready()
                if ready:
                    self._set_step("fetch", "done", detail)
                    return
                last_error = result.get("stderr") or detail or last_error

            # Retry once with the other channel if first failed.
            alt = "ghproxy" if channel != "ghproxy" else "github"
            if alt != channel:
                self._log(f"retry fetch with channel={alt}")
                try:
                    self._fetch_inprocess(alt)
                    ready, detail = self._browser_ready()
                    if ready:
                        self._set_step("fetch", "done", detail)
                        return
                except Exception as exc:
                    last_error = str(exc)

        raise RuntimeError(last_error)

    def _step_verify(self) -> None:
        self._set_step("verify", "running")
        ready, detail = self._browser_ready()
        if not ready:
            raise RuntimeError(detail or "verification failed")
        ver = detail
        try:
            from camoufox.pkgman import installed_verstr

            ver = installed_verstr()
        except Exception:
            if not self.is_frozen:
                version = self._run(self.camoufox_command("version"), timeout=20)
                ver = (version.get("stdout") or version.get("stderr") or detail).strip()
        self._set_step("verify", "done", ver or detail)
        self._log(f"verify ok: {ver or detail}")
