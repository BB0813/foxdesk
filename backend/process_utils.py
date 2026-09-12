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
    """Stop a worker and its whole child tree.

    On Windows ``Popen.terminate()`` is ``TerminateProcess`` — an immediate
    hard kill of the single process that leaves browser children orphaned and
    never runs the worker's own cleanup. So on Windows we always go through
    ``taskkill /T`` (graceful WM_CLOSE first, then /F), which also reaches
    grandchildren processes.
    """
    if process.poll() is not None:
        return
    pid = process.pid
    if os.name == "nt":
        # Graceful tree close first (workers get a chance to close contexts).
        kill_process_tree(pid, force=False)
        if _wait(process, min(grace, 5.0)):
            return
        kill_process_tree(pid, force=True)
        if _wait(process, 3.0):
            return
        try:
            process.kill()
        except Exception:
            pass
        _wait(process, 3.0)
        return
    try:
        process.terminate()
    except Exception:
        pass
    if _wait(process, grace):
        return
    kill_process_tree(pid, force=False)
    if _wait(process, 3.0):
        return
    kill_process_tree(pid, force=True)
    try:
        process.kill()
    except Exception:
        pass
    _wait(process, 3.0)


def _wait(process: subprocess.Popen[Any], timeout: float) -> bool:
    try:
        process.wait(timeout=timeout)
        return True
    except Exception:
        return False


# Windows Job Object: workers + their browser children live inside a job with
# KILL_ON_JOB_CLOSE, so a crashed/force-killed manager cannot orphan browsers.
_job_handles: list[Any] = []


def assign_job_object(process: subprocess.Popen[Any]) -> bool:
    """Put a freshly spawned process into a kill-on-close job (Windows only)."""
    if os.name != "nt":
        return False
    try:
        import ctypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

        class IO_COUNTERS(ctypes.Structure):
            _fields_ = [(n, ctypes.c_ulonglong) for n in (
                "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
                "ReadTransferCount", "WriteTransferCount", "OtherTransferCount",
            )]

        class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", ctypes.c_longlong),
                ("PerJobUserTimeLimit", ctypes.c_longlong),
                ("LimitFlags", ctypes.c_uint32),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", ctypes.c_uint32),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", ctypes.c_uint32),
                ("SchedulingClass", ctypes.c_uint32),
            ]

        class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
                ("IoInfo", IO_COUNTERS),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t),
            ]

        JobObjectExtendedLimitInformation = 9
        JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000

        handle = kernel32.CreateJobObjectW(None, None)
        if not handle:
            return False
        info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not kernel32.SetInformationJobObject(
            handle, JobObjectExtendedLimitInformation, ctypes.byref(info), ctypes.sizeof(info)
        ):
            kernel32.CloseHandle(handle)
            return False
        if not kernel32.AssignProcessToJobObject(handle, process._handle):
            kernel32.CloseHandle(handle)
            return False
        # Keep the handle open for the manager's lifetime: closing it would
        # immediately kill the assigned tree. Freed on process exit.
        _job_handles.append(handle)
        return True
    except Exception:
        return False


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
