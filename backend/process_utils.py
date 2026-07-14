from __future__ import annotations

import os
import signal
import subprocess
import sys
from typing import Any


CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def kill_process_tree(pid: int, *, force: bool = False) -> None:
    """Terminate a process and its children. Best-effort across platforms."""
    if pid <= 0:
        return
    if os.name == "nt":
        args = ["taskkill", "/PID", str(pid), "/T"]
        if force:
            args.append("/F")
        try:
            subprocess.run(
                args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
                creationflags=CREATE_NO_WINDOW,
            )
        except Exception:
            pass
        return

    # POSIX: try process group first, then direct signal.
    try:
        os.killpg(pid, signal.SIGKILL if force else signal.SIGTERM)
        return
    except Exception:
        pass
    try:
        os.kill(pid, signal.SIGKILL if force else signal.SIGTERM)
    except Exception:
        pass


def stop_popen(process: subprocess.Popen[Any], *, grace: float = 8.0) -> None:
    if process.poll() is not None:
        return
    pid = process.pid
    try:
        process.terminate()
    except Exception:
        pass
    try:
        process.wait(timeout=grace)
        return
    except Exception:
        pass
    kill_process_tree(pid, force=False)
    try:
        process.wait(timeout=3)
        return
    except Exception:
        pass
    kill_process_tree(pid, force=True)
    try:
        process.kill()
    except Exception:
        pass
    try:
        process.wait(timeout=3)
    except Exception:
        pass


def parse_worker_event(line: str) -> dict[str, Any] | None:
    line = (line or "").strip()
    if not line.startswith("{"):
        return None
    try:
        import json

        data = json.loads(line)
        if isinstance(data, dict) and "event" in data:
            return data
    except Exception:
        return None
    return None
