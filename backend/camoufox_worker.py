from __future__ import annotations

import json
import signal
import sys
import time
from pathlib import Path
from typing import Any


running = True


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

    vendor = (profile.get("navigator_vendor") or "").strip()
    # navigator.vendor is not a first-class Camoufox property; keep only platform.

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
    # Prefer webgl_config tuple when OS is known; otherwise inject config keys.
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

            # Screen constrains random fingerprint generation bounds.
            kwargs["screen"] = Screen(max_width=max(width, 800), max_height=max(height, 600))
        except Exception:
            pass

    webgl_vendor = (profile.get("webgl_vendor") or "").strip()
    webgl_renderer = (profile.get("webgl_renderer") or "").strip()
    if webgl_vendor and webgl_renderer and os_name and os_name != "auto":
        # webgl_config requires OS; may still fail if pair not in sample DB — fall back to config.
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
        # BrowserContext or Page
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
    # Pre-validate via launch_options when available to catch invalid webgl pairs early.
    try:
        from camoufox.utils import launch_options

        probe = dict(kwargs)
        # launch_options does not accept persistent_context / user_data_dir the same way;
        # strip playwright-only keys for probe.
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
        # Return kwargs anyway; actual launch will surface the error.
        return kwargs


def run_browser(profile: dict[str, Any]) -> int:
    try:
        from camoufox.sync_api import Camoufox
    except Exception as exc:
        emit("error", message=f"failed to import camoufox: {exc}")
        return 2

    kwargs = safe_launch_kwargs(profile)
    startup_url = (profile.get("startup_url") or "").strip()
    emit("launching", kwargs={k: ("***" if k == "proxy" else v) for k, v in kwargs.items()})

    try:
        with Camoufox(**kwargs) as browser_or_context:
            # persistent_context returns BrowserContext; otherwise Browser
            if hasattr(browser_or_context, "new_page"):
                page = browser_or_context.new_page()
                apply_imported_cookies(browser_or_context, profile)
            else:
                page = browser_or_context.new_page()
                apply_imported_cookies(page, profile)

            if startup_url:
                emit("navigate", url=startup_url)
                page.goto(startup_url, wait_until="domcontentloaded", timeout=45000)
            emit("ready", mode="browser")
            while running:
                time.sleep(0.5)
    except Exception as exc:
        emit("error", message=str(exc))
        return 1
    finally:
        emit("stopped")
    return 0


def run_server(profile: dict[str, Any]) -> int:
    try:
        from camoufox.server import launch_server
    except Exception as exc:
        emit("error", message=f"failed to import camoufox.server: {exc}")
        return 2

    kwargs = safe_launch_kwargs(profile)
    # Server path does not use persistent_context the same way
    kwargs.pop("persistent_context", None)
    kwargs.pop("user_data_dir", None)
    emit("launching", mode="server")
    try:
        # launch_server is blocking / NoReturn in upstream; still guard for failures
        launch_server(**kwargs)
        emit("ready", mode="server")
        while running:
            time.sleep(0.5)
    except Exception as exc:
        emit("error", message=str(exc))
        return 1
    finally:
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
        return run_server(profile)
    return run_browser(profile)


if __name__ == "__main__":
    raise SystemExit(main())
