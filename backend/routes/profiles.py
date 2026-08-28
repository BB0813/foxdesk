"""Profile routes: CRUD, import/export, cookies, templates, fingerprint
generation and static consistency checks."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from backend.core import (
    PROFILES_DIR,
    Profile,
    ProxyConfig,
    RUNTIME_DIR,
    activity,
    now_iso,
    store,
)
from backend.cookie_io import find_cookies_sqlite, parse_netscape_cookies
from backend.engine_meta import normalize_engine_name
from backend.models import (
    ApplySuggestionRequest,
    BulkProxyRequest,
    ImportProfilesRequest,
    ProfileIn,
)
from backend.profile_logic import (
    apply_proxy_pool_to_profile,
    detect_google_chrome_install,
    environment_risks_for_profile,
    resolve_user_data_dir,
)
from backend.templates_data import profile_templates

router = APIRouter()


@router.get("/api/profiles")
def list_profiles() -> list[Profile]:
    return store.all()


@router.post("/api/profiles")
def create_profile(profile: ProfileIn) -> Profile:
    data = profile.model_dump()
    engine = normalize_engine_name(data.get("engine"))
    data["engine"] = engine
    if data.get("user_data_dir"):
        data["user_data_dir"] = str(resolve_user_data_dir(data["user_data_dir"]))
    elif data.get("name"):
        slug = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in data["name"]).strip("-") or "profile"
        if engine == "chromium" and not slug.endswith("-chromium"):
            slug = f"{slug}-chromium"
        data["user_data_dir"] = str(PROFILES_DIR / slug)
    created = store.create(ProfileIn(**data))
    activity.log("profile_create", f"{created.name} engine={engine}")
    return created


@router.get("/api/profiles/export")
def export_profiles() -> JSONResponse:
    return JSONResponse(
        {
            "exported_at": now_iso(),
            "schema": "camoufox-manager.profiles.v1",
            "profiles": [profile.model_dump() for profile in store.all()],
        }
    )


@router.post("/api/profiles/import")
def import_profiles(request: ImportProfilesRequest) -> list[Profile]:
    try:
        return store.import_profiles(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


@router.post("/api/profiles/{profile_id}/clone")
def clone_profile(profile_id: str) -> Profile:
    try:
        return store.clone(profile_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="profile not found") from None


@router.put("/api/profiles/{profile_id}")
def update_profile(profile_id: str, profile: ProfileIn) -> Profile:
    try:
        data = profile.model_dump()
        if data.get("user_data_dir"):
            data["user_data_dir"] = str(resolve_user_data_dir(data["user_data_dir"]))
        updated = store.update(profile_id, ProfileIn(**data))
        activity.log("profile_update", updated.name)
        return updated
    except KeyError:
        raise HTTPException(status_code=404, detail="profile not found") from None


@router.delete("/api/profiles/{profile_id}")
def delete_profile(profile_id: str) -> dict[str, bool]:
    try:
        store.delete(profile_id)
        activity.log("profile_delete", profile_id)
        return {"ok": True}
    except KeyError:
        raise HTTPException(status_code=404, detail="profile not found") from None


@router.post("/api/profiles/{profile_id}/open-data-dir")
def open_profile_data_dir(profile_id: str) -> dict[str, Any]:
    try:
        profile = store.get(profile_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="profile not found") from None
    if not profile.user_data_dir:
        raise HTTPException(status_code=409, detail="profile has no user_data_dir")

    target = Path(profile.user_data_dir).expanduser()
    target.mkdir(parents=True, exist_ok=True)
    try:
        if os.name == "nt":
            os.startfile(str(target))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(target)])
        else:
            subprocess.Popen(["xdg-open", str(target)])
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from None
    return {"ok": True, "path": str(target)}


# --- Random Fingerprint Generation ---
COMMON_TIMEZONES = [
    "America/New_York", "America/Chicago", "America/Los_Angeles", "America/Denver",
    "Europe/London", "Europe/Berlin", "Europe/Paris", "Europe/Moscow",
    "Asia/Tokyo", "Asia/Shanghai", "Asia/Seoul", "Asia/Kolkata",
    "Australia/Sydney", "Pacific/Auckland",
]

WINDOWS_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:154.0) Gecko/20100101 Firefox/154.0",
]

MACOS_USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/19.2 Safari/605.1.15",
]

LINUX_USER_AGENTS = [
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:154.0) Gecko/20100101 Firefox/154.0",
]

WEBGL_VENDORS = ["Google Inc. (NVIDIA)", "Google Inc. (AMD)", "Google Inc. (Intel)", "Apple Inc."]
WEBGL_RENDERERS = [
    "ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 SUPER Direct3D11 vs_5_0 ps_5_0)",
    "ANGLE (AMD, AMD Radeon RX 580 Direct3D11 vs_5_0 ps_5_0)",
    "ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0)",
    "Apple GPU",
]

SCREEN_CONFIGS = [
    (1920, 1080, 24, 1.0),
    (2560, 1440, 24, 1.0),
    (1366, 768, 24, 1.0),
    (1536, 864, 24, 1.25),
    (1440, 900, 24, 1.0),
    (3840, 2160, 24, 1.5),
    (1280, 720, 24, 1.0),
]

LOCALES = ["en-US", "en-GB", "de-DE", "fr-FR", "es-ES", "ja-JP", "zh-CN", "zh-TW", "ko-KR", "pt-BR", "ru-RU", "it-IT"]

WEBRTC_MODES = ["default", "disable", "public_only", "force_proxy"]
MEDIA_MODES = ["default", "random", "empty"]


@router.post("/api/fingerprint/generate")
def generate_fingerprint(target_os: str = "auto") -> dict[str, Any]:
    """Generate a randomized fingerprint profile."""
    import random as _rand
    os_choice = _rand.choice(["windows", "macos", "linux"]) if target_os == "auto" else target_os
    if os_choice == "windows":
        ua = _rand.choice(WINDOWS_USER_AGENTS)
        platform_str = "Win32"
        vendor_str = "Google Inc."
    elif os_choice == "macos":
        ua = _rand.choice(MACOS_USER_AGENTS)
        platform_str = "MacIntel"
        vendor_str = "Apple Computer, Inc."
    else:
        ua = _rand.choice(LINUX_USER_AGENTS)
        platform_str = "Linux x86_64"
        vendor_str = "Google Inc."

    screen = _rand.choice(SCREEN_CONFIGS)
    locale = _rand.choice(LOCALES)
    timezone = _rand.choice(COMMON_TIMEZONES)

    from backend.fingerprint_presets import FONT_PACKS, normalize_os_key

    pack_key = normalize_os_key(os_choice)
    return {
        "navigator_platform": platform_str,
        "navigator_vendor": vendor_str,
        "screen_width": screen[0],
        "screen_height": screen[1],
        "screen_color_depth": screen[2],
        "device_pixel_ratio": screen[3],
        "hardware_concurrency": _rand.choice([4, 6, 8, 12, 16]),
        "device_memory": _rand.choice([4, 8, 16]),
        "canvas_noise": True,
        "webgl_vendor": _rand.choice(WEBGL_VENDORS),
        "webgl_renderer": _rand.choice(WEBGL_RENDERERS),
        "audio_noise": True,
        "font_pack": pack_key,
        "fonts": list(FONT_PACKS.get(pack_key, [])),
        "timezone": timezone,
        "locale": locale,
        "webrtc_mode": "disable",
        "media_devices": "random",
        "user_agent": ua,
        "ua_ch_platform": "Windows" if os_choice == "windows" else ("macOS" if os_choice == "macos" else "Linux"),
        "ua_ch_mobile": False,
        "consistency_policy": "normal",
    }


# --- Cookie Management ---
@router.get("/api/profiles/{profile_id}/cookies")
def export_cookies(profile_id: str):
    try:
        profile = store.get(profile_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="profile not found") from None
    if not profile.user_data_dir:
        raise HTTPException(status_code=409, detail="profile has no user_data_dir")
    user_data = Path(profile.user_data_dir).expanduser()
    imported_file = user_data / "imported_cookies.json"
    cookies_path = find_cookies_sqlite(user_data)

    # Prefer live sqlite; fallback to previously imported JSON
    if cookies_path is None:
        if imported_file.exists():
            try:
                data = json.loads(imported_file.read_text(encoding="utf-8"))
                cookies = data if isinstance(data, list) else data.get("cookies", [])
                return JSONResponse({
                    "cookies": cookies,
                    "count": len(cookies),
                    "source": "imported_cookies.json",
                })
            except Exception as exc:
                raise HTTPException(status_code=500, detail=f"Failed to read imported cookies: {exc}") from None
        return JSONResponse({"cookies": [], "count": 0, "source": None})

    try:
        import sqlite3
        # Copy to temp to avoid Windows lock issues while browser is open
        tmp = RUNTIME_DIR / f"cookies-export-{uuid.uuid4().hex}.sqlite"
        shutil.copy2(cookies_path, tmp)
        try:
            conn = sqlite3.connect(str(tmp))
            cursor = conn.execute(
                "SELECT host, name, value, path, expiry, isSecure, isHttpOnly, sameSite FROM moz_cookies"
            )
            cookies = []
            for row in cursor.fetchall():
                cookies.append({
                    "host": row[0],
                    "domain": row[0],
                    "name": row[1],
                    "value": row[2],
                    "path": row[3],
                    "expires": row[4],
                    "secure": bool(row[5]),
                    "httpOnly": bool(row[6]),
                    "sameSite": row[7] or "Lax",
                })
            conn.close()
        finally:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
        return JSONResponse({
            "cookies": cookies,
            "count": len(cookies),
            "source": str(cookies_path),
        })
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read cookies: {exc}") from None


@router.post("/api/profiles/{profile_id}/cookies")
def import_cookies(profile_id: str, request: dict[str, Any]):
    try:
        profile = store.get(profile_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="profile not found") from None
    if not profile.user_data_dir:
        raise HTTPException(status_code=409, detail="profile has no user_data_dir")

    cookies = request.get("cookies", [])
    raw_text = request.get("raw_text") or request.get("text") or ""
    if raw_text and not cookies:
        text = str(raw_text)
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                cookies = parsed
            elif isinstance(parsed, dict):
                cookies = parsed.get("cookies") or []
        except Exception:
            cookies = parse_netscape_cookies(text)
    if not isinstance(cookies, list):
        raise HTTPException(status_code=400, detail="cookies must be a list or Netscape/JSON text")

    cookies_dir = Path(profile.user_data_dir).expanduser()
    cookies_dir.mkdir(parents=True, exist_ok=True)
    cookies_file = cookies_dir / "imported_cookies.json"
    cookies_file.write_text(json.dumps(cookies, ensure_ascii=False, indent=2), encoding="utf-8")
    activity.log("cookies_import", f"{profile.name}: {len(cookies)}")
    return {
        "ok": True,
        "count": len(cookies),
        "path": str(cookies_file),
        "note": "Cookies are applied on next session launch via Playwright add_cookies.",
    }


# --- Templates ---
@router.get("/api/templates")
def list_templates() -> list[dict[str, Any]]:
    return profile_templates()


@router.post("/api/templates/{template_id}/create")
def create_from_template(template_id: str) -> Profile:
    template = next((t for t in profile_templates() if t["id"] == template_id), None)
    if not template:
        raise HTTPException(status_code=404, detail="template not found")
    data = dict(template["profile"])
    slug = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in data.get("name", "template")).strip("-")
    engine = normalize_engine_name(data.get("engine"))
    # Isolate user_data per engine so camoufox/chromium never share a profile dir.
    suffix = "chromium" if engine == "chromium" else "camoufox"
    data["user_data_dir"] = str(PROFILES_DIR / f"{slug}-{suffix}-{uuid.uuid4().hex[:6]}")
    data.setdefault("proxy", {"server": "", "username": "", "password": ""})
    data.setdefault("proxy_id", "")
    data.setdefault("addons", [])
    data.setdefault("extra_args", [])
    data.setdefault("fonts", [])
    if engine == "chromium":
        data.setdefault("chromium_backend", "auto")
    created = store.create(ProfileIn(**data))
    activity.log("template_create", f"{template_id} -> {created.name} engine={engine}")
    return created


# --- Bulk Proxy Import ---
@router.post("/api/profiles/bulk-proxy")
def bulk_proxy_import(request: BulkProxyRequest) -> dict[str, Any]:
    """Import proxies and assign to profiles. Format: one proxy per line, e.g. socks5://user:pass@host:port"""
    updated = 0
    profiles = store.all()
    target_ids = set(request.profile_ids) if request.profile_ids else {p.id for p in profiles}
    for i, proxy_str in enumerate(request.proxies):
        proxy_str = proxy_str.strip()
        if not proxy_str:
            continue
        if "://" not in proxy_str:
            proxy_str = f"http://{proxy_str}"
        # Find profile to update
        for profile in profiles:
            if profile.id in target_ids:
                idx = next((j for j, p in enumerate(profiles) if p.id == profile.id), None)
                if idx is not None:
                    dump = profile.model_dump()
                    dump["proxy"] = ProxyConfig(server=proxy_str).model_dump()
                    dump["updated_at"] = now_iso()
                    profiles[idx] = Profile(**dump)
                    updated += 1
                    target_ids.discard(profile.id)
                    break
        if not target_ids:
            break
    store.save_all(profiles)
    return {"ok": True, "updated": updated}


# --- D-B5: one-click risk-suggestion application ---
_SUGGESTION_APPLIERS = {
    "chromium_bundled_build": lambda profile: {"chromium_channel": "chrome"},
}


@router.post("/api/profiles/{profile_id}/apply-suggestion")
def apply_risk_suggestion(profile_id: str, request: ApplySuggestionRequest) -> Profile:
    """Apply a whitelisted environment-risk suggestion to a profile (D-B5).

    Currently supports: chromium_bundled_build -> chromium_channel=chrome
    (requires local Google Chrome detection to succeed).
    """
    applier = _SUGGESTION_APPLIERS.get((request.code or "").strip())
    if applier is None:
        raise HTTPException(status_code=400, detail=f"no automated suggestion for code: {request.code}")
    try:
        profile = store.get(profile_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="profile not found") from None
    if (profile.engine or "") != "chromium":
        raise HTTPException(status_code=409, detail="suggestion applies to chromium-engine profiles only")
    if request.code == "chromium_bundled_build" and not detect_google_chrome_install().get("installed"):
        raise HTTPException(status_code=409, detail="Google Chrome was not detected on this machine")
    data = profile.model_dump()
    data.update(applier(profile))
    updated = store.update(profile_id, ProfileIn(**data))
    activity.log("risk_suggestion_apply", f"{profile.name}: {request.code}")
    return updated


# --- Fingerprint Check ---
@router.get("/api/profiles/{profile_id}/fingerprint-check")
def fingerprint_check(profile_id: str) -> dict[str, Any]:
    """Static consistency + environment risk scoring (not a live anti-detect guarantee)."""
    try:
        profile = store.get(profile_id)
        profile = apply_proxy_pool_to_profile(profile)
    except KeyError:
        raise HTTPException(status_code=404, detail="profile not found") from None

    check_url = "https://browserleaks.com/javascript"
    has_proxy = bool((profile.proxy and profile.proxy.server) or profile.proxy_id)
    engine = normalize_engine_name(getattr(profile, "engine", None))
    checks = {
        "mode": profile.mode,
        "engine": engine,
        "chromium_backend": getattr(profile, "chromium_backend", None) or "",
        "chromium_channel": getattr(profile, "chromium_channel", None) or "",
        "os": profile.os,
        "headless": profile.headless,
        "proxy": (profile.proxy.server if profile.proxy and profile.proxy.server else "") or ("proxy_id:" + profile.proxy_id if profile.proxy_id else "none"),
        "geoip": profile.geoip,
        "screen": f"{profile.screen_width}x{profile.screen_height}" if profile.screen_width else "not set",
        "platform": profile.navigator_platform or "not set",
        "vendor": profile.navigator_vendor or "not set",
        "webgl": f"{profile.webgl_vendor} / {profile.webgl_renderer}" if profile.webgl_vendor else "not set",
        "canvas_noise": profile.canvas_noise,
        "audio_noise": profile.audio_noise,
        "block_webrtc": profile.block_webrtc,
        "webrtc_mode": profile.webrtc_mode,
        "timezone": profile.timezone or "not set",
        "locale": profile.locale or "not set",
        "persistent_context": profile.persistent_context,
        "humanize": profile.humanize,
        "font_pack": getattr(profile, "font_pack", None) or "",
        "media_devices": getattr(profile, "media_devices", None) or "default",
        "tags": list(profile.tags or [])[:16],
    }

    issues: list[str] = []
    if profile.headless:
        issues.append("Headless is on — payment/3DS pages often refuse this outright")
    if (profile.mode or "").lower() == "server":
        issues.append("Server mode is not suitable for interactive checkout")
    if not profile.navigator_platform and (profile.os or "auto") == "auto":
        issues.append("Platform/OS not pinned")
    if profile.screen_width and profile.screen_height:
        if profile.screen_width < 800 or profile.screen_height < 600:
            issues.append("Screen resolution too small for desktop checkout")
    if not profile.webgl_vendor and not profile.block_webgl:
        issues.append("WebGL vendor/renderer not set (will use Camoufox default)")
    if profile.block_webgl:
        issues.append("WebGL is blocked — many gateways expect GPU parameters")
    if profile.webrtc_mode == "default" and not profile.block_webrtc:
        issues.append("WebRTC not disabled — may leak real IP beside proxy")
    if has_proxy and not profile.geoip:
        issues.append("Proxy without geoip — timezone/locale may disagree with exit IP")
    if has_proxy and not (profile.timezone or "").strip():
        issues.append("Proxy without timezone")
    if has_proxy and not (profile.locale or "").strip():
        issues.append("Proxy without locale")
    if not has_proxy:
        issues.append("No proxy — exit IP is your real network")
    if profile.locale and profile.timezone:
        locale_tz_map = {
            "en-US": "America/",
            "en-GB": "Europe/London",
            "de-DE": "Europe/",
            "fr-FR": "Europe/",
            "ja-JP": "Asia/Tokyo",
            "zh-CN": "Asia/Shanghai",
            "zh-TW": "Asia/Taipei",
            "ko-KR": "Asia/Seoul",
        }
        for loc_prefix, tz_prefix in locale_tz_map.items():
            if profile.locale.startswith(loc_prefix) and profile.timezone.startswith(tz_prefix):
                break
        else:
            issues.append(
                f"Locale ({profile.locale}) and timezone ({profile.timezone}) may be inconsistent"
            )

    risks = environment_risks_for_profile(profile)
    high = sum(1 for r in risks if r.get("level") == "high")
    medium = sum(1 for r in risks if r.get("level") == "medium")
    score = 100 - (len(issues) * 12) - high * 8 - medium * 3
    return {
        "profile_id": profile_id,
        "checks": checks,
        "issues": issues,
        "environment_risks": risks,
        "score": max(0, min(100, score)),
        "check_url": check_url,
        "note": (
            "Static consistency only — not a payment / AI signup-pass guarantee. "
            "Camoufox is Firefox-based; many payment stacks score Chromium fingerprints differently."
        ),
    }
