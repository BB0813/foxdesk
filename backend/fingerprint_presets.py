"""Phase B fingerprint presets — fonts / media device catalogues.

Best-effort configuration helpers for commercial-style *consistency*, not a
kernel-level anti-detect stack. Used by workers, generate_fingerprint, templates.
"""

from __future__ import annotations

from typing import Any

# Common desktop font families observed on stock OS installs (subset).
# Order matters for some naive detectors that hash the enumeration order.
FONT_PACKS: dict[str, list[str]] = {
    "windows": [
        "Arial",
        "Arial Black",
        "Calibri",
        "Cambria",
        "Cambria Math",
        "Comic Sans MS",
        "Consolas",
        "Courier New",
        "Georgia",
        "Impact",
        "Lucida Console",
        "Lucida Sans Unicode",
        "Microsoft Sans Serif",
        "Palatino Linotype",
        "Segoe UI",
        "Segoe UI Emoji",
        "Segoe UI Symbol",
        "Tahoma",
        "Times New Roman",
        "Trebuchet MS",
        "Verdana",
        "Wingdings",
    ],
    "macos": [
        "American Typewriter",
        "Arial",
        "Arial Black",
        "Arial Narrow",
        "Avenir",
        "Avenir Next",
        "Courier",
        "Courier New",
        "Geneva",
        "Georgia",
        "Helvetica",
        "Helvetica Neue",
        "Lucida Grande",
        "Menlo",
        "Monaco",
        "Palatino",
        "San Francisco",
        "Times",
        "Times New Roman",
        "Trebuchet MS",
        "Verdana",
    ],
    "linux": [
        "DejaVu Sans",
        "DejaVu Sans Mono",
        "DejaVu Serif",
        "FreeMono",
        "FreeSans",
        "FreeSerif",
        "Liberation Mono",
        "Liberation Sans",
        "Liberation Serif",
        "Noto Color Emoji",
        "Noto Sans",
        "Noto Serif",
        "Ubuntu",
        "Ubuntu Mono",
    ],
}

# Synthetic media device labels for Chromium init-script (enumerateDevices).
MEDIA_DEVICE_SETS: dict[str, list[dict[str, str]]] = {
    "empty": [],
    "random": [
        {
            "deviceId": "default",
            "kind": "audioinput",
            "label": "Default - Microphone Array (Realtek Audio)",
            "groupId": "g-audio-in",
        },
        {
            "deviceId": "communications",
            "kind": "audioinput",
            "label": "Communications - Microphone Array (Realtek Audio)",
            "groupId": "g-audio-in",
        },
        {
            "deviceId": "default",
            "kind": "audiooutput",
            "label": "Default - Speakers (Realtek Audio)",
            "groupId": "g-audio-out",
        },
        {
            "deviceId": "communications",
            "kind": "audiooutput",
            "label": "Communications - Speakers (Realtek Audio)",
            "groupId": "g-audio-out",
        },
        {
            "deviceId": "cam0",
            "kind": "videoinput",
            "label": "Integrated Camera (04f2:b6d9)",
            "groupId": "g-video",
        },
    ],
    # "default" for Chromium means: do not override enumerateDevices
}


def normalize_os_key(os_name: str | None) -> str:
    raw = (os_name or "windows").strip().lower()
    if raw in {"mac", "macos", "darwin", "osx"}:
        return "macos"
    if raw in {"linux", "ubuntu", "debian"}:
        return "linux"
    if raw in {"win", "windows", "win32"}:
        return "windows"
    return "windows"


def resolve_font_list(profile: dict[str, Any]) -> list[str]:
    """Return explicit fonts or OS pack when profile requests auto pack.

    Convention:
      - fonts empty + font_pack in {auto, windows, macos, linux} → pack
      - fonts non-empty → use as-is
      - font_pack empty and fonts empty → [] (no override)
    """
    fonts = [str(f).strip() for f in (profile.get("fonts") or []) if str(f).strip()]
    if fonts:
        return fonts
    pack = (profile.get("font_pack") or "").strip().lower()
    if not pack or pack in {"none", "off", "manual"}:
        return []
    if pack in {"auto", "os", "default_pack"}:
        pack = normalize_os_key(profile.get("os"))
    return list(FONT_PACKS.get(pack, FONT_PACKS["windows"]))


def resolve_media_devices(profile: dict[str, Any]) -> tuple[str, list[dict[str, str]] | None]:
    """Return (mode, device_list_or_None).

    None device list means: leave browser default (mode=default).
    """
    mode = (profile.get("media_devices") or "default").strip().lower()
    if mode not in {"default", "random", "empty"}:
        mode = "default"
    if mode == "default":
        return mode, None
    if mode == "empty":
        return mode, []
    return mode, list(MEDIA_DEVICE_SETS["random"])


def commercial_windows_desktop_hints() -> dict[str, Any]:
    """Sensible Phase B defaults for a Windows desktop-like Chromium profile."""
    return {
        "os": "windows",
        "navigator_platform": "Win32",
        "navigator_vendor": "Google Inc.",
        "ua_ch_platform": "Windows",
        "ua_ch_mobile": False,
        "font_pack": "windows",
        "fonts": list(FONT_PACKS["windows"]),
        "media_devices": "random",
        "hardware_concurrency": 8,
        "device_memory": 8,
        "screen_width": 1920,
        "screen_height": 1080,
        "screen_color_depth": 24,
        "device_pixel_ratio": 1.0,
        "webrtc_mode": "disable",
        "block_webrtc": True,
        "headless": False,
        "consistency_policy": "normal",
    }
