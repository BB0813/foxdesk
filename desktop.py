from __future__ import annotations

import atexit
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import webbrowser
from pathlib import Path


HOST = "127.0.0.1"
DEFAULT_PORT = 8765
APP_NAME = "FoxDesk"
APP_VERSION = "1.4.2"
LOCK_DIR = Path(tempfile.gettempdir()) / APP_NAME
LOCK_FILE = LOCK_DIR / "instance.lock"
MUTEX_NAME = "Local\\FoxDesk_SingleInstance_Mutex"
_mutex_handle = None
_tray_icon = None


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


ROOT = app_root()


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


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform == "win32":
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x100000, False, pid)  # SYNCHRONIZE
        if handle:
            kernel32.CloseHandle(handle)
            return True
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def acquire_single_instance_lock() -> bool:
    """Acquire a single-instance lock. Prefer Windows named mutex, fallback to lock file."""
    global _mutex_handle

    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            # use_last_error=True makes ctypes.get_last_error() capture the
            # real CreateMutexW result instead of a possibly-reset value.
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
            kernel32.CreateMutexW.restype = wintypes.HANDLE
            handle = kernel32.CreateMutexW(None, False, MUTEX_NAME)
            if handle:
                last_error = ctypes.get_last_error()
                # ERROR_ALREADY_EXISTS = 183
                if last_error == 183:
                    kernel32.CloseHandle(handle)
                    return False
                _mutex_handle = handle

                def release_mutex() -> None:
                    try:
                        if _mutex_handle:
                            kernel32.CloseHandle(_mutex_handle)
                    except Exception:
                        pass

                atexit.register(release_mutex)
                return True
        except Exception:
            pass

    try:
        LOCK_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        return False

    if LOCK_FILE.exists():
        try:
            pid_text = LOCK_FILE.read_text(encoding="utf-8").strip()
            if pid_text and _pid_alive(int(pid_text)):
                return False
        except (ValueError, OSError):
            pass

    try:
        fd = os.open(str(LOCK_FILE), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(str(os.getpid()))
    except FileExistsError:
        try:
            pid_text = LOCK_FILE.read_text(encoding="utf-8").strip()
            if pid_text and _pid_alive(int(pid_text)):
                return False
            LOCK_FILE.write_text(str(os.getpid()), encoding="utf-8")
        except OSError:
            return False
    except OSError:
        try:
            LOCK_FILE.write_text(str(os.getpid()), encoding="utf-8")
        except OSError:
            return False

    def release_lock() -> None:
        try:
            if LOCK_FILE.exists():
                current = LOCK_FILE.read_text(encoding="utf-8").strip()
                if current == str(os.getpid()):
                    LOCK_FILE.unlink()
        except OSError:
            pass

    atexit.register(release_lock)
    return True


def wait_until_ready(port: int, timeout: float = 20.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.4)
            if sock.connect_ex((HOST, port)) == 0:
                return
        time.sleep(0.2)
    raise RuntimeError(f"server did not start on {HOST}:{port}")


def start_server(port: int) -> subprocess.Popen[str]:
    creationflags = 0x08000000 if os.name == "nt" else 0
    # Keep server output on disk: DEVNULL made frozen install problems
    # undiagnosable.
    try:
        log_dir = Path(tempfile.gettempdir()) / "FoxDesk"
        log_dir.mkdir(parents=True, exist_ok=True)
        out_log = open(log_dir / "server.out.log", "ab")
        err_log = open(log_dir / "server.err.log", "ab")
    except Exception:
        out_log = err_log = subprocess.DEVNULL
    if getattr(sys, "frozen", False):
        cmd = [sys.executable, "--serve", str(port)]
        return subprocess.Popen(
            cmd,
            stdout=out_log,
            stderr=err_log,
            text=True,
            creationflags=creationflags,
        )
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.app:app", "--host", HOST, "--port", str(port)],
        cwd=str(ROOT),
        stdout=out_log,
        stderr=err_log,
        text=True,
        creationflags=creationflags,
    )


def run_worker_mode(runtime_path: str) -> int:
    """Run engine worker inside the same frozen binary or source tree.

    Phase A: dispatch camoufox vs chromium from runtime JSON ``engine`` field.
    """
    sys.argv = [sys.argv[0], runtime_path]
    engine = "camoufox"
    try:
        import json
        from pathlib import Path

        data = json.loads(Path(runtime_path).read_text(encoding="utf-8"))
        if isinstance(data, dict):
            raw = str(data.get("engine") or "camoufox").strip().lower()
            if raw in {"chromium", "chrome", "pw", "playwright"}:
                engine = "chromium"
    except Exception as exc:
        # A missing/corrupt runtime must fail fast — silently defaulting the
        # engine would launch the wrong browser stack.
        try:
            sys.stderr.write(f"worker abort: unreadable runtime {runtime_path}: {exc}\n")
        except Exception:
            pass
        return 65
    try:
        if engine == "chromium":
            from backend.chromium_worker import main as worker_main
        else:
            from backend.camoufox_worker import main as worker_main

        return int(worker_main())
    except Exception as exc:
        try:
            sys.stderr.write(f"worker failed ({engine}): {exc}\n")
        except Exception:
            pass
        return 1


def run_serve_mode(port: int) -> int:
    import uvicorn

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    uvicorn.run("backend.app:app", host=HOST, port=port, log_level="error")
    return 0


def _stop_all_sessions(port: int) -> None:
    try:
        import urllib.request

        headers = {"Content-Type": "application/json"}
        # Same per-process token the UI gets; the server mirrors it into the
        # instance lock dir so the desktop shell can call the local API.
        try:
            token = (LOCK_DIR / "api-token").read_text(encoding="utf-8").strip()
            if token:
                headers["X-FoxDesk-Token"] = token
        except Exception:
            pass
        req = urllib.request.Request(
            f"http://{HOST}:{port}/api/sessions/stop-all",
            data=b"{}",
            headers=headers,
            method="POST",
        )
        urllib.request.urlopen(req, timeout=8).read()
    except Exception:
        pass


def _open_ui_safely(url: str) -> None:
    try:
        webbrowser.open(url)
    except Exception:
        pass


_server_process: subprocess.Popen[str] | None = None
_quit_requested = False


def start_tray(port: int, window=None) -> None:
    """Optional system tray (pystray). Fail silently if unavailable."""
    global _tray_icon
    if _tray_icon is not None:
        # Already running (e.g. WebView failed after tray start) — reuse it.
        return
    try:
        import pystray
        from PIL import Image
    except Exception:
        return

    icon_path = ROOT / "static" / "logo.png"
    try:
        image = Image.open(icon_path)
    except Exception:
        image = Image.new("RGB", (64, 64), color=(6, 182, 212))

    url = f"http://{HOST}:{port}"

    def on_show(icon, item):  # noqa: ARG001
        try:
            if window is not None:
                window.show()
                window.restore()
                return
        except Exception:
            pass
        _open_ui_safely(url)

    def on_open_ui(icon, item):  # noqa: ARG001
        _open_ui_safely(url)

    def on_stop_sessions(icon, item):  # noqa: ARG001
        _stop_all_sessions(port)

    def on_quit(icon, item):  # noqa: ARG001
        global _quit_requested
        _quit_requested = True
        try:
            _stop_all_sessions(port)
        except Exception:
            pass
        try:
            icon.stop()
        except Exception:
            pass
        try:
            if window is not None:
                window.destroy()
        except Exception:
            pass
        # Fallback UI path: main thread is blocked in server.wait(); stopping
        # the server releases it so the normal finally-cleanup can run.
        try:
            if window is None and _server_process is not None and _server_process.poll() is None:
                from backend.process_utils import stop_popen

                stop_popen(_server_process, grace=8)
        except Exception:
            pass

    menu = pystray.Menu(
        pystray.MenuItem(f"FoxDesk {APP_VERSION}", on_show, default=True),
        pystray.MenuItem("Open UI", on_open_ui),
        pystray.MenuItem("Stop All Sessions", on_stop_sessions),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", on_quit),
    )
    _tray_icon = pystray.Icon("FoxDesk", image, f"FoxDesk {APP_VERSION}", menu)

    def run_icon() -> None:
        try:
            _tray_icon.run()
        except Exception:
            pass

    threading.Thread(target=run_icon, daemon=True).start()


def _staged_dir(name: str) -> Path | None:
    """Mirror a bundle folder to an ASCII local path when the install path is
    unsafe for .NET assembly loading (non-ASCII characters get mangled by
    clr_loader's netfx host; network-mapped drives hit .NET CAS zoning)."""
    import tempfile

    source = Path(name)
    try:
        str(source).encode("ascii")
    except UnicodeEncodeError:
        pass
    else:
        exe_drive = os.path.splitdrive(str(source))[0]
        tmp_drive = os.path.splitdrive(tempfile.gettempdir())[0]
        if exe_drive and exe_drive.lower() == tmp_drive.lower():
            return None  # already ASCII on a local drive
    try:
        import shutil

        dest = Path(tempfile.gettempdir()) / "FoxDesk" / source.name
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, dest, dirs_exist_ok=True)
        return dest
    except Exception:
        return None


def _prepare_frozen_dotnet() -> None:
    """Make pythonnet/pywebview loadable from non-ASCII or network installs.

    1. pythonnet resolves Python.Runtime.dll via ``Path(__file__).parent/"runtime"``
       — point the package ``__file__`` at an ASCII staging copy.
    2. pywebview loads WebView2 interop assemblies by absolute path from
       ``webview/lib`` — reroute ``interop_dll_path`` to a staged copy.
    Best-effort: on failure the WebView→system-browser fallback still applies.
    """
    try:
        import pythonnet

        staged = _staged_dir(str(Path(pythonnet.__file__).parent / "runtime"))
        if staged is not None:
            pythonnet.__file__ = str(staged.parent / "__init__.py")
    except Exception:
        pass
    try:
        import webview
        import webview.util as wutil

        lib = Path(webview.__file__).parent / "lib"
        staged = _staged_dir(str(lib)) if lib.is_dir() else None
        if staged is not None:
            _orig = wutil.interop_dll_path

            def _staged_interop_dll_path(dll_name: str) -> str:  # noqa: ANN001
                try:
                    rel = None
                    for candidate in (
                        staged / dll_name,
                        staged / "runtimes" / dll_name / "native",
                    ):
                        if candidate.exists():
                            rel = candidate
                            break
                    if rel is None:
                        return _orig(dll_name)
                    return str(rel)
                except Exception:
                    return _orig(dll_name)

            wutil.interop_dll_path = _staged_interop_dll_path
    except Exception:
        pass


def main() -> int:
    if len(sys.argv) >= 3 and sys.argv[1] == "--serve":
        return run_serve_mode(int(sys.argv[2]))

    if len(sys.argv) >= 3 and sys.argv[1] == "--worker":
        return run_worker_mode(sys.argv[2])

    if not acquire_single_instance_lock():
        print("Another instance of FoxDesk is already running.")
        print("Please close the existing instance or wait for it to exit.")
        return 1

    port = find_port()
    server = start_server(port)
    global _server_process
    _server_process = server
    try:
        wait_until_ready(port)
        url = f"http://{HOST}:{port}"
        try:
            _prepare_frozen_dotnet()
            import webview

            window = webview.create_window(
                f"FoxDesk {APP_VERSION}",
                url,
                width=1400,
                height=900,
                min_size=(1060, 680),
                text_select=True,
                background_color="#0a0e17",
            )
            start_tray(port, window)

            def on_closing() -> bool:
                # Minimize-like behavior: keep process if tray is active
                if _tray_icon is not None:
                    try:
                        window.hide()
                        return False
                    except Exception:
                        return True
                return True

            try:
                window.events.closing += on_closing
            except Exception:
                pass
            webview.start()
        except Exception as exc:
            # ImportError or frozen pythonnet/webview failures → system browser + tray.
            print(f"WebView unavailable ({type(exc).__name__}: {exc}); opening system browser.")
            start_tray(port, None)  # no-op if the pre-failure tray survived
            _open_ui_safely(url)
            print(f"FoxDesk {APP_VERSION}: {url}")
            server.wait()
    except KeyboardInterrupt:
        return 130
    finally:
        try:
            if _tray_icon is not None:
                _tray_icon.stop()
        except Exception:
            pass
        if server.poll() is None:
            # Ask backend to stop sessions then terminate server tree
            try:
                _stop_all_sessions(port)
            except Exception:
                pass
            from backend.process_utils import stop_popen

            stop_popen(server, grace=5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
