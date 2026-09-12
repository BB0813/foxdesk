"""Windows Job Object: worker trees die with the manager even on crash."""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

from backend.process_utils import CREATE_NO_WINDOW, assign_job_object


@pytest.mark.skipif(os.name != "nt", reason="Job Objects are Windows-only")
def test_job_object_kills_child_tree() -> None:
    import ctypes
    import threading
    import time

    from backend import process_utils

    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; print('started', flush=True); time.sleep(60)"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        creationflags=CREATE_NO_WINDOW,
    )
    try:
        proc.stdout.readline()  # child started
        assert assign_job_object(proc), "AssignProcessToJobObject failed"
        handle = process_utils._job_handles[-1]
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        # Simulate the manager dying: terminating/closing the job must take
        # the assigned child (and any grandchildren) with it.
        kernel32.TerminateJobObject(handle, 1)
        assert proc.wait(timeout=10) != 0
    finally:
        if proc.poll() is None:
            proc.kill()
        threading.Timer(0.1, lambda: process_utils._job_handles.remove(handle) if handle in process_utils._job_handles else None).start()


@pytest.mark.skipif(os.name == "nt", reason="POSIX branch is a no-op by design")
def test_assign_job_object_noop_on_posix() -> None:
    assert assign_job_object(None) is False
