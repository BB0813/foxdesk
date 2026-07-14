from __future__ import annotations

import shutil
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
        path_cmd = self.camoufox_command("path")
        result = self._run(path_cmd, timeout=12)
        path_text = (result.get("stdout") or "").strip()
        if not result.get("ok") or not path_text:
            return True
        return not Path(path_text).exists()

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
            with self.lock:
                self.state.status = "failed"
                self.state.error = str(exc)
                self.state.finished_at = time.time()
            self._log(f"[failed] {exc}")

    def _step_check(self) -> None:
        self._set_step("check", "running")
        frozen = self.is_frozen
        detail = f"frozen={frozen} python={sys.version.split()[0]}"
        self._log(detail)
        self._set_step("check", "done", detail)

    def _step_package(self) -> None:
        self._set_step("package", "running")
        if self.is_frozen:
            # Bundled app already ships camoufox; pip against FoxDesk.exe is invalid.
            if self.import_available("camoufox"):
                self._set_step("package", "skipped", "bundled in app")
                self._log("package: camoufox already bundled (frozen)")
                return
            raise RuntimeError("Camoufox package missing from application bundle")

        if self.import_available("camoufox"):
            self._set_step("package", "skipped", "already installed")
            self._log("package: already installed")
            return

        cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "camoufox"]
        result = self._run(cmd, timeout=300)
        if not result.get("ok") or not self.import_available("camoufox"):
            raise RuntimeError(result.get("stderr") or "pip install camoufox failed")
        self._set_step("package", "done", "installed")

    def _fetch_commands(self, channel: str) -> list[list[str]]:
        commands: list[list[str]] = []
        prefix = self.channel_prefix(channel)
        if prefix:
            commands.append(self.camoufox_command("fetch", "-u", prefix))
        # Always keep official as fallback
        official = self.camoufox_command("fetch")
        if not commands or commands[0] != official:
            commands.append(official)
        # Common GitHub mirror fallback for restricted networks
        if channel != "ghproxy":
            commands.append(self.camoufox_command("fetch", "-u", "https://ghproxy.com/"))
        # de-dup while preserving order
        seen: set[tuple[str, ...]] = set()
        unique: list[list[str]] = []
        for cmd in commands:
            key = tuple(cmd)
            if key in seen:
                continue
            seen.add(key)
            unique.append(cmd)
        return unique

    def _browser_ready(self) -> tuple[bool, str]:
        if not self.import_available("camoufox"):
            return False, "camoufox import failed"
        result = self._run(self.camoufox_command("path"), timeout=20)
        path_text = (result.get("stdout") or "").strip()
        if not path_text:
            return False, result.get("stderr") or "empty path"
        if not Path(path_text).exists():
            return False, f"path missing: {path_text}"
        return True, path_text

    def _step_fetch(self) -> None:
        self._set_step("fetch", "running")
        ready, detail = self._browser_ready()
        if ready:
            self._set_step("fetch", "skipped", detail)
            self._log(f"fetch: browser already present at {detail}")
            return

        channel = self.state.channel or "github"
        last_error = "fetch failed"
        for cmd in self._fetch_commands(channel):
            self._log(f"trying fetch via: {' '.join(cmd)}")
            result = self._run(cmd, timeout=600)
            ready, detail = self._browser_ready()
            if ready:
                self._set_step("fetch", "done", detail)
                return
            last_error = result.get("stderr") or detail or last_error
        raise RuntimeError(last_error)

    def _step_verify(self) -> None:
        self._set_step("verify", "running")
        ready, detail = self._browser_ready()
        if not ready:
            raise RuntimeError(detail or "verification failed")
        version = self._run(self.camoufox_command("version"), timeout=20)
        ver = (version.get("stdout") or version.get("stderr") or "").strip()
        self._set_step("verify", "done", ver or detail)
        self._log(f"verify ok: {ver or detail}")
