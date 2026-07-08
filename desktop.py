from __future__ import annotations

import atexit
import os
import socket
import subprocess
import sys
import tempfile
import time
import webbrowser
from pathlib import Path


ROOT = Path(__file__).resolve().parent
if getattr(sys, "frozen", False):
    ROOT = Path(sys._MEIPASS)
HOST = "127.0.0.1"
DEFAULT_PORT = 8765
APP_NAME = "CamoufoxManager"
LOCK_DIR = Path(tempfile.gettempdir()) / APP_NAME
LOCK_FILE = LOCK_DIR / "instance.lock"


def find_port(start: int = DEFAULT_PORT) -> int:
    port = start
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((HOST, port))
                return port
            except OSError:
                port += 1


def acquire_single_instance_lock() -> bool:
    """Try to acquire a single-instance lock using a lock file.
    Returns True if lock acquired, False if another instance is running."""
    try:
        LOCK_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        return False

    if LOCK_FILE.exists():
        # Check if the process holding the lock is still alive
        try:
            pid_text = LOCK_FILE.read_text(encoding="utf-8").strip()
            if pid_text:
                pid = int(pid_text)
                # Check if process exists
                if sys.platform == "win32":
                    import ctypes
                    kernel32 = ctypes.windll.kernel32
                    handle = kernel32.OpenProcess(0x100000, False, pid)  # SYNCHRONIZE
                    if handle:
                        kernel32.CloseHandle(handle)
                        return False
                else:
                    try:
                        os.kill(pid, 0)
                        return False
                    except OSError:
                        pass  # Process doesn't exist
        except (ValueError, OSError):
            pass  # Invalid lock file, we can take it

    # Write our PID to the lock file
    try:
        LOCK_FILE.write_text(str(os.getpid()), encoding="utf-8")
    except OSError:
        return False

    # Register cleanup on exit
    def release_lock() -> None:
        try:
            if LOCK_FILE.exists():
                LOCK_FILE.unlink()
        except OSError:
            pass

    atexit.register(release_lock)
    return True


def wait_until_ready(port: int, timeout: float = 12.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.4)
            if sock.connect_ex((HOST, port)) == 0:
                return
        time.sleep(0.2)
    raise RuntimeError(f"server did not start on {HOST}:{port}")


def start_server(port: int) -> subprocess.Popen[str]:
    if getattr(sys, "frozen", False):
        # PyInstaller bundle: launch exe itself with --serve arg
        cmd = [sys.executable, "--serve", str(port)]
        creationflags = 0x08000000 if os.name == "nt" else 0
        return subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
            creationflags=creationflags,
        )
    else:
        return subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "backend.app:app",
             "--host", HOST, "--port", str(port)],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )


def main() -> int:
    # Handle --serve mode (called by frozen exe to run uvicorn backend)
    if len(sys.argv) >= 3 and sys.argv[1] == "--serve":
        port = int(sys.argv[2])
        import uvicorn
        uvicorn.run("backend.app:app", host=HOST, port=port, log_level="error")
        return 0

    # Try to acquire single-instance lock
    if not acquire_single_instance_lock():
        print("Another instance of Camoufox Manager is already running.")
        print("Please close the existing instance or wait for it to exit.")
        return 1

    port = find_port()
    server = start_server(port)
    try:
        wait_until_ready(port)
        url = f"http://{HOST}:{port}"
        try:
            import webview

            window = webview.create_window(
                "FoxDesk",
                url,
                width=1400,
                height=900,
                min_size=(1060, 680),
                text_select=True,
                background_color="#0a0e17",
            )
            webview.start()
            _ = window
        except ImportError:
            webbrowser.open(url)
            print(f"Camoufox Manager: {url}")
            server.wait()
    except KeyboardInterrupt:
        return 130
    finally:
        if server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
