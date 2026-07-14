from __future__ import annotations

import json
import re
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


running = True
_page_holder: dict[str, Any] = {"page": None, "context": None}
_cmd_lock = threading.RLock()


def emit(event: str, **payload: Any) -> None:
    print(json.dumps({"event": event, **payload}, ensure_ascii=False), flush=True)


def stop_handler(signum: int, frame: object) -> None:
    global running
    running = False
    emit("signal", signum=signum)


def compact(value: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in value.items() if v not in (None, "", [], {})}


def build_proxy(profile: dict[str, Any]) -> dict[str, str] | None:
    proxy = profile.get("proxy") or {}
    server = (proxy.get("server") or "").strip()
    if not server:
        return None
    result = {"server": server}
    username = (proxy.get("username") or "").strip()
    password = proxy.get("password") or ""
    if username:
        result["username"] = username
    if password:
        result["password"] = password
    return result


def build_config(profile: dict[str, Any]) -> dict[str, Any]:
    """Map profile fingerprint fields to Camoufox config properties."""
    config: dict[str, Any] = {}

    platform = (profile.get("navigator_platform") or "").strip()
    if platform:
        config["navigator.platform"] = platform

    width = int(profile.get("screen_width") or 0)
    height = int(profile.get("screen_height") or 0)
    if width > 0:
        config["screen.width"] = width
        config["screen.availWidth"] = width
    if height > 0:
        config["screen.height"] = height
        config["screen.availHeight"] = height

    color_depth = int(profile.get("screen_color_depth") or 0)
    if color_depth > 0:
        config["screen.colorDepth"] = color_depth
        config["screen.pixelDepth"] = color_depth

    timezone = (profile.get("timezone") or "").strip()
    if timezone:
        config["timezone"] = timezone

    if profile.get("canvas_noise") is False:
        config["canvas:aaOffset"] = 0
        config["canvas:aaCapOffset"] = False

    media_devices = (profile.get("media_devices") or "default").strip()
    if media_devices == "empty":
        config["mediaDevices:enabled"] = False
        config["mediaDevices:micros"] = 0
        config["mediaDevices:speakers"] = 0
        config["mediaDevices:webcams"] = 0
    elif media_devices == "random":
        config["mediaDevices:enabled"] = True
        config["mediaDevices:micros"] = 1
        config["mediaDevices:speakers"] = 1
        config["mediaDevices:webcams"] = 1

    webrtc_mode = (profile.get("webrtc_mode") or "default").strip()
    if webrtc_mode == "public_only":
        config["webrtc:localipv4"] = ""
        config["webrtc:localipv6"] = ""

    webgl_vendor = (profile.get("webgl_vendor") or "").strip()
    webgl_renderer = (profile.get("webgl_renderer") or "").strip()
    if webgl_vendor:
        config["webGl:vendor"] = webgl_vendor
    if webgl_renderer:
        config["webGl:renderer"] = webgl_renderer

    return config


def build_kwargs(profile: dict[str, Any]) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "headless": bool(profile.get("headless", False)),
    }

    os_name = profile.get("os")
    if os_name and os_name != "auto":
        kwargs["os"] = os_name

    if profile.get("persistent_context", True):
        kwargs["persistent_context"] = True
        user_data_dir = profile.get("user_data_dir")
        if user_data_dir:
            kwargs["user_data_dir"] = str(Path(user_data_dir).expanduser())

    if profile.get("humanize"):
        kwargs["humanize"] = True
    if profile.get("geoip"):
        kwargs["geoip"] = True
    if profile.get("locale"):
        kwargs["locale"] = profile["locale"]

    proxy = build_proxy(profile)
    if proxy:
        kwargs["proxy"] = proxy

    toggles = [
        "block_images",
        "block_webrtc",
        "block_webgl",
        "disable_coop",
        "enable_cache",
    ]
    for key in toggles:
        if key in profile:
            kwargs[key] = bool(profile[key])

    webrtc_mode = (profile.get("webrtc_mode") or "default").strip()
    if webrtc_mode == "disable":
        kwargs["block_webrtc"] = True

    if kwargs.get("disable_coop"):
        kwargs["i_know_what_im_doing"] = True

    addons = profile.get("addons") or []
    if addons:
        kwargs["addons"] = addons

    extra_args = profile.get("extra_args") or []
    if extra_args:
        kwargs["args"] = extra_args

    fonts = profile.get("fonts") or []
    if fonts:
        kwargs["fonts"] = fonts

    width = int(profile.get("screen_width") or 0)
    height = int(profile.get("screen_height") or 0)
    if width > 0 and height > 0:
        kwargs["window"] = (width, height)
        try:
            from browserforge.fingerprints import Screen

            kwargs["screen"] = Screen(max_width=max(width, 800), max_height=max(height, 600))
        except Exception:
            pass

    webgl_vendor = (profile.get("webgl_vendor") or "").strip()
    webgl_renderer = (profile.get("webgl_renderer") or "").strip()
    if webgl_vendor and webgl_renderer and os_name and os_name != "auto":
        kwargs["webgl_config"] = (webgl_vendor, webgl_renderer)

    config = build_config(profile)
    if config:
        kwargs["config"] = config

    return compact(kwargs)


def playwright_cookies(raw_cookies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    converted: list[dict[str, Any]] = []
    for item in raw_cookies:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        value = item.get("value")
        if not name or value is None:
            continue
        cookie: dict[str, Any] = {
            "name": str(name),
            "value": str(value),
            "path": item.get("path") or "/",
        }
        domain = item.get("domain") or item.get("host")
        url = item.get("url")
        if domain:
            cookie["domain"] = str(domain)
        elif url:
            cookie["url"] = str(url)
        else:
            continue

        expires = item.get("expires") if "expires" in item else item.get("expiry")
        if expires not in (None, "", 0, "0"):
            try:
                cookie["expires"] = float(expires)
            except (TypeError, ValueError):
                pass
        if "secure" in item or "isSecure" in item:
            cookie["secure"] = bool(item.get("secure", item.get("isSecure")))
        if "httpOnly" in item or "isHttpOnly" in item:
            cookie["httpOnly"] = bool(item.get("httpOnly", item.get("isHttpOnly")))
        same_site = item.get("sameSite")
        if same_site in ("Strict", "Lax", "None"):
            cookie["sameSite"] = same_site
        converted.append(cookie)
    return converted


def apply_imported_cookies(context_or_page: Any, profile: dict[str, Any]) -> int:
    user_data_dir = (profile.get("user_data_dir") or "").strip()
    if not user_data_dir:
        return 0
    cookies_file = Path(user_data_dir).expanduser() / "imported_cookies.json"
    if not cookies_file.exists():
        return 0
    try:
        raw = json.loads(cookies_file.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            raw = raw.get("cookies") or []
        if not isinstance(raw, list):
            return 0
        cookies = playwright_cookies(raw)
        if not cookies:
            return 0
        if hasattr(context_or_page, "add_cookies"):
            context_or_page.add_cookies(cookies)
        elif hasattr(context_or_page, "context"):
            context_or_page.context.add_cookies(cookies)
        else:
            return 0
        emit("cookies_imported", count=len(cookies))
        return len(cookies)
    except Exception as exc:
        emit("cookies_import_error", message=str(exc))
        return 0


def safe_launch_kwargs(profile: dict[str, Any]) -> dict[str, Any]:
    """Build kwargs; if webgl_config sampling fails, drop it and rely on config."""
    kwargs = build_kwargs(profile)
    try:
        from camoufox.utils import launch_options

        probe = dict(kwargs)
        probe.pop("persistent_context", None)
        probe.pop("user_data_dir", None)
        launch_options(**probe)
        return kwargs
    except Exception as exc:
        message = str(exc)
        if "webgl_config" in kwargs and ("WebGL" in message or "webgl" in message.lower()):
            emit("warning", message=f"webgl_config rejected, falling back to config: {message}")
            kwargs = dict(kwargs)
            kwargs.pop("webgl_config", None)
            return kwargs
        return kwargs


def command_path_for(profile_path: Path) -> Path:
    return profile_path.with_suffix(".cmd.jsonl")


def result_path_for(profile_path: Path) -> Path:
    return profile_path.with_suffix(".result.jsonl")


def write_result(profile_path: Path, payload: dict[str, Any]) -> None:
    path = result_path_for(profile_path)
    try:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except OSError as exc:
        emit("warning", message=f"failed to write command result: {exc}")


def validate_nav_url(url: str) -> str:
    value = (url or "").strip()
    if not value:
        raise ValueError("url is required")
    if value.startswith("about:"):
        return value
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("url must be http(s) or about:")
    return value


def probe_fingerprint(page: Any) -> dict[str, Any]:
    script = """
    () => {
      const nav = window.navigator || {};
      const screenObj = window.screen || {};
      let webglVendor = '';
      let webglRenderer = '';
      try {
        const canvas = document.createElement('canvas');
        const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
        if (gl) {
          const dbg = gl.getExtension('WEBGL_debug_renderer_info');
          if (dbg) {
            webglVendor = gl.getParameter(dbg.UNMASKED_VENDOR_WEBGL) || '';
            webglRenderer = gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) || '';
          }
        }
      } catch (e) {}
      let timezone = '';
      try { timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || ''; } catch (e) {}
      return {
        userAgent: nav.userAgent || '',
        platform: nav.platform || '',
        language: nav.language || '',
        languages: Array.from(nav.languages || []),
        hardwareConcurrency: nav.hardwareConcurrency || 0,
        deviceMemory: nav.deviceMemory || 0,
        screen: {
          width: screenObj.width || 0,
          height: screenObj.height || 0,
          colorDepth: screenObj.colorDepth || 0,
        },
        timezone,
        webglVendor,
        webglRenderer,
        href: location.href || '',
      };
    }
    """
    return page.evaluate(script)


def handle_command(cmd: dict[str, Any], profile_path: Path) -> None:
    req_id = cmd.get("id") or ""
    action = (cmd.get("cmd") or cmd.get("action") or "").strip().lower()
    page = _page_holder.get("page")

    def reply(**payload: Any) -> None:
        body = {"id": req_id, "cmd": action, "ok": payload.get("ok", True), **payload}
        write_result(profile_path, body)
        emit("command_result", **body)

    try:
        if action in {"stop", "quit", "exit"}:
            global running
            running = False
            reply(ok=True, message="stopping")
            return
        if action == "navigate":
            if page is None:
                reply(ok=False, error="no active page (browser mode only)")
                return
            url = validate_nav_url(str(cmd.get("url") or ""))
            emit("navigate", url=url, request_id=req_id)
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            reply(ok=True, url=url, href=getattr(page, "url", url))
            return
        if action in {"fingerprint", "fingerprint_probe", "probe"}:
            if page is None:
                reply(ok=False, error="no active page (browser mode only)")
                return
            data = probe_fingerprint(page)
            reply(ok=True, report=data)
            return
        if action == "ping":
            reply(ok=True, ready=page is not None)
            return
        reply(ok=False, error=f"unknown command: {action}")
    except Exception as exc:
        reply(ok=False, error=str(exc))


def command_loop(profile_path: Path) -> None:
    path = command_path_for(profile_path)
    # Ensure empty command file exists.
    try:
        if not path.exists():
            path.write_text("", encoding="utf-8")
    except OSError:
        pass
    offset = 0
    while running:
        try:
            if not path.exists():
                time.sleep(0.3)
                continue
            data = path.read_bytes()
            if len(data) < offset:
                offset = 0
            if len(data) == offset:
                time.sleep(0.25)
                continue
            chunk = data[offset:].decode("utf-8", errors="replace")
            offset = len(data)
            for line in chunk.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    cmd = json.loads(line)
                except Exception:
                    emit("warning", message=f"invalid command line: {line[:120]}")
                    continue
                if isinstance(cmd, dict):
                    with _cmd_lock:
                        handle_command(cmd, profile_path)
        except Exception as exc:
            emit("warning", message=f"command loop error: {exc}")
            time.sleep(0.5)


def run_browser(profile: dict[str, Any], profile_path: Path) -> int:
    try:
        from camoufox.sync_api import Camoufox
    except Exception as exc:
        emit("error", message=f"failed to import camoufox: {exc}")
        return 2

    kwargs = safe_launch_kwargs(profile)
    startup_url = (profile.get("startup_url") or "").strip()
    emit("launching", kwargs={k: ("***" if k == "proxy" else v) for k, v in kwargs.items()})

    cmd_thread = threading.Thread(target=command_loop, args=(profile_path,), daemon=True)
    cmd_thread.start()

    try:
        with Camoufox(**kwargs) as browser_or_context:
            if hasattr(browser_or_context, "new_page"):
                page = browser_or_context.new_page()
                apply_imported_cookies(browser_or_context, profile)
                _page_holder["context"] = browser_or_context
            else:
                page = browser_or_context.new_page()
                apply_imported_cookies(page, profile)
                _page_holder["context"] = getattr(page, "context", None)
            _page_holder["page"] = page

            if startup_url:
                emit("navigate", url=startup_url)
                page.goto(startup_url, wait_until="domcontentloaded", timeout=45000)
            emit("ready", mode="browser", control="cmd.jsonl")
            # Optional auto probe after ready
            if profile.get("_auto_fingerprint_probe"):
                try:
                    report = probe_fingerprint(page)
                    emit("fingerprint_report", report=report)
                    write_result(profile_path, {"id": "auto", "cmd": "fingerprint", "ok": True, "report": report})
                except Exception as exc:
                    emit("warning", message=f"auto fingerprint probe failed: {exc}")
            while running:
                time.sleep(0.5)
    except Exception as exc:
        emit("error", message=str(exc))
        return 1
    finally:
        _page_holder["page"] = None
        _page_holder["context"] = None
        emit("stopped")
    return 0


_WS_RE = re.compile(r"(wss?://[^\s\"'<>]+)", re.I)
# Common Camoufox / Playwright server banners.
_WS_LABEL_RE = re.compile(
    r"(?:ws(?:s)?\s*endpoint|playwright\s*endpoint|listening\s+on|browser\s*server|cdp\s*endpoint)"
    r"\s*[:=]\s*(wss?://[^\s\"'<>]+)",
    re.I,
)
_HOSTPORT_RE = re.compile(r"(?:127\.0\.0\.1|localhost|0\.0\.0\.0):(\d{2,5})", re.I)


def _extract_ws_endpoint(text: str) -> str | None:
    if not text:
        return None
    m = _WS_LABEL_RE.search(text)
    if m:
        return m.group(1).rstrip(").,]}\"';")
    m = _WS_RE.search(text)
    if m:
        return m.group(1).rstrip(").,]}\"';")
    # Last-resort: bare host:port from server banners → assume ws://
    if "endpoint" in text.lower() or "listening" in text.lower() or "playwright" in text.lower():
        hp = _HOSTPORT_RE.search(text)
        if hp:
            port = hp.group(1)
            host = "127.0.0.1"
            return f"ws://{host}:{port}"
    return None


def run_server(profile: dict[str, Any], profile_path: Path) -> int:
    try:
        from camoufox.server import launch_server
    except Exception as exc:
        emit("error", message=f"failed to import camoufox.server: {exc}")
        return 2

    kwargs = safe_launch_kwargs(profile)
    kwargs.pop("persistent_context", None)
    kwargs.pop("user_data_dir", None)
    emit("launching", mode="server")

    endpoint_holder: dict[str, str | None] = {"ws": None}
    endpoint_path = profile_path.with_suffix(".ws")

    def publish_endpoint(ws: str, raw: str = "") -> None:
        if not ws or endpoint_holder.get("ws") == ws:
            return
        endpoint_holder["ws"] = ws
        try:
            endpoint_path.write_text(ws + "\n", encoding="utf-8")
        except OSError:
            pass
        emit("endpoint", ws_endpoint=ws, raw=(raw or ws)[:300])
        emit("ready", mode="server", ws_endpoint=ws)

    # Mirror stdout/stderr from nested prints when possible.
    # launch_server typically blocks and prints the endpoint.
    class _StdoutTee:
        def __init__(self, original):
            self._original = original
            self._buf = ""

        def write(self, s: str) -> int:
            if not isinstance(s, str):
                s = str(s)
            try:
                self._original.write(s)
                self._original.flush()
            except Exception:
                pass
            self._buf += s
            while True:
                parts = re.split(r"\r\n|\n|\r", self._buf, maxsplit=1)
                if len(parts) == 1:
                    break
                line, self._buf = parts[0], parts[1]
                line = line.strip()
                if not line:
                    continue
                ws = _extract_ws_endpoint(line)
                if ws:
                    publish_endpoint(ws, raw=line)
                else:
                    emit("server_log", message=line[:500])
            # Also scan incomplete buffer for early endpoint prints without newline.
            if endpoint_holder.get("ws") is None and len(self._buf) > 12:
                ws = _extract_ws_endpoint(self._buf)
                if ws:
                    publish_endpoint(ws, raw=self._buf)
            return len(s)

        def flush(self) -> None:
            try:
                self._original.flush()
            except Exception:
                pass

        def isatty(self) -> bool:
            try:
                return bool(self._original.isatty())
            except Exception:
                return False

        def fileno(self) -> int:
            return self._original.fileno()

    # Lightweight command loop for server mode: ping / stop / endpoint query.
    def server_command_loop() -> None:
        global running
        path = command_path_for(profile_path)
        try:
            if not path.exists():
                path.write_text("", encoding="utf-8")
        except OSError:
            pass
        offset = 0
        while running:
            try:
                if not path.exists():
                    time.sleep(0.3)
                    continue
                data = path.read_bytes()
                if len(data) < offset:
                    offset = 0
                if len(data) == offset:
                    time.sleep(0.3)
                    continue
                chunk = data[offset:].decode("utf-8", errors="replace")
                offset = len(data)
                for line in chunk.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        cmd = json.loads(line)
                    except Exception:
                        continue
                    if not isinstance(cmd, dict):
                        continue
                    req_id = cmd.get("id") or ""
                    action = (cmd.get("cmd") or cmd.get("action") or "").strip().lower()
                    if action in {"stop", "quit", "exit"}:
                        running = False
                        write_result(profile_path, {"id": req_id, "cmd": action, "ok": True, "message": "stopping"})
                        emit("command_result", id=req_id, cmd=action, ok=True)
                    elif action in {"ping", "endpoint", "ws"}:
                        ws = endpoint_holder.get("ws")
                        if ws is None:
                            # Try sidecar file written earlier.
                            try:
                                if endpoint_path.exists():
                                    ws = endpoint_path.read_text(encoding="utf-8").strip() or None
                            except OSError:
                                pass
                        write_result(
                            profile_path,
                            {
                                "id": req_id,
                                "cmd": action,
                                "ok": True,
                                "ws_endpoint": ws,
                                "ready": ws is not None,
                            },
                        )
                        emit("command_result", id=req_id, cmd=action, ok=True, ws_endpoint=ws)
                    else:
                        write_result(
                            profile_path,
                            {
                                "id": req_id,
                                "cmd": action,
                                "ok": False,
                                "error": "command not supported in server mode (use browser mode for navigate/fingerprint)",
                            },
                        )
            except Exception as exc:
                emit("warning", message=f"server command loop error: {exc}")
                time.sleep(0.5)

    cmd_thread = threading.Thread(target=server_command_loop, daemon=True)
    cmd_thread.start()

    old_out, old_err = sys.stdout, sys.stderr
    tee = _StdoutTee(old_out)
    # Keep emit working: emit writes to print -> tee -> original.
    sys.stdout = tee  # type: ignore[assignment]
    sys.stderr = tee  # type: ignore[assignment]
    try:
        # Mark process live even before endpoint is known.
        emit("ready", mode="server", ws_endpoint=None, note="waiting for camoufox server endpoint")
        # Some camoufox builds accept port=0; keep kwargs as-is for compatibility.
        launch_server(**kwargs)
    except Exception as exc:
        # restore before emit error fully
        sys.stdout, sys.stderr = old_out, old_err
        emit("error", message=str(exc))
        return 1
    finally:
        sys.stdout, sys.stderr = old_out, old_err
        try:
            endpoint_path.unlink(missing_ok=True)
        except OSError:
            pass
        emit("stopped")
    return 0


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: camoufox_worker.py <runtime-profile.json>", file=sys.stderr)
        return 64

    signal.signal(signal.SIGTERM, stop_handler)
    signal.signal(signal.SIGINT, stop_handler)

    profile_path = Path(sys.argv[1])
    if not profile_path.exists():
        emit("error", message=f"runtime profile not found: {profile_path}")
        return 66
    try:
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
    except Exception as exc:
        emit("error", message=f"invalid runtime profile: {exc}")
        return 65
    mode = profile.get("mode", "browser")
    if mode == "server":
        return run_server(profile, profile_path)
    return run_browser(profile, profile_path)


if __name__ == "__main__":
    raise SystemExit(main())
