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
    if kwargs.get("disable_coop"):
        kwargs["i_know_what_im_doing"] = True

    addons = profile.get("addons") or []
    if addons:
        kwargs["addons"] = addons

    extra_args = profile.get("extra_args") or []
    if extra_args:
        kwargs["args"] = extra_args

    # Fingerprint parameters
    fp_fields = {
        "navigator_platform": "navigator_platform",
        "navigator_vendor": "navigator_vendor",
        "screen_width": "screen_width",
        "screen_height": "screen_height",
        "screen_color_depth": "screen_color_depth",
        "device_pixel_ratio": "device_pixel_ratio",
        "canvas_noise": "canvas_noise",
        "webgl_vendor": "webgl_vendor",
        "webgl_renderer": "webgl_renderer",
        "audio_noise": "audio_noise",
        "webrtc_mode": "webrtc_mode",
        "media_devices": "media_devices",
        "timezone": "timezone",
        "keyboard_layout": "keyboard_layout",
    }
    for profile_key, kwarg_key in fp_fields.items():
        val = profile.get(profile_key)
        if val is not None and val != "" and val != 0 and val != 0.0:
            kwargs[kwarg_key] = val

    fonts = profile.get("fonts") or []
    if fonts:
        kwargs["fonts"] = fonts

    return compact(kwargs)


def run_browser(profile: dict[str, Any]) -> int:
    try:
        from camoufox.sync_api import Camoufox
    except Exception as exc:
        emit("error", message=f"failed to import camoufox: {exc}")
        return 2

    kwargs = build_kwargs(profile)
    startup_url = (profile.get("startup_url") or "").strip()
    emit("launching", kwargs={k: ("***" if k == "proxy" else v) for k, v in kwargs.items()})

    try:
        with Camoufox(**kwargs) as browser_or_context:
            page = browser_or_context.new_page()
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

    kwargs = build_kwargs(profile)
    emit("launching", mode="server")
    try:
        server = launch_server(**kwargs)
        ws_endpoint = getattr(server, "ws_endpoint", None) or getattr(server, "wsEndpoint", None)
        emit("ready", mode="server", ws_endpoint=ws_endpoint)
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
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    mode = profile.get("mode", "browser")
    if mode == "server":
        return run_server(profile)
    return run_browser(profile)


if __name__ == "__main__":
    raise SystemExit(main())
