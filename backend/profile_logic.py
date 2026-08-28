"""Profile-domain logic: path resolution, launch validation, environment risk
scoring, and proxy-pool assignment."""
from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any

from backend.core import PROFILES_DIR, Profile, ProxyConfig, now_iso, proxy_pool, settings_store
from backend.engine_meta import (
    chromium_install_hint,
    normalize_chromium_backend_name,
    normalize_engine_name,
)
from backend.engine_tools import (
    camoufox_path_info,
    import_available,
    resolve_chromium_backend,
)

_rr_proxy_index = 0
_rr_proxy_lock = threading.Lock()


def resolve_user_data_dir(raw: str) -> Path:
    """Resolve relative profile dirs under APPDATA profiles root."""
    value = (raw or "").strip()
    if not value:
        return PROFILES_DIR / "unnamed"
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = PROFILES_DIR / path
    return path


def normalize_profile_paths(profile: Profile) -> Profile:
    """Ensure user_data_dir is absolute under the app data directory when relative."""
    if not profile.user_data_dir:
        return profile
    resolved = resolve_user_data_dir(profile.user_data_dir)
    if str(resolved) != profile.user_data_dir:
        data = profile.model_dump()
        data["user_data_dir"] = str(resolved)
        return Profile(**data)
    return profile


def validate_profile_for_launch(profile: Profile) -> list[str]:
    """Validate profile before launching. Returns list of error messages."""
    errors: list[str] = []
    engine = normalize_engine_name(getattr(profile, "engine", None))

    # 1. Camoufox binary only required for camoufox engine
    if engine == "camoufox":
        try:
            path_result = camoufox_path_info()
            if not path_result.get("ok") or not path_result.get("stdout", "").strip():
                errors.append("Camoufox browser binary not found. Complete first-run setup / fetch first.")
            else:
                browser_path = Path(path_result["stdout"].strip())
                if not browser_path.exists():
                    errors.append(f"Camoufox browser path does not exist: {browser_path}")
        except Exception as exc:
            errors.append(f"Failed to check Camoufox browser path: {exc}")

    # 2. Check user data directory is writable (if persistent context)
    if profile.persistent_context and profile.user_data_dir:
        user_data_dir = resolve_user_data_dir(profile.user_data_dir)
        try:
            user_data_dir.mkdir(parents=True, exist_ok=True)
            test_file = user_data_dir / ".write_test"
            test_file.write_text("test", encoding="utf-8")
            test_file.unlink()
        except PermissionError:
            errors.append(f"User data directory is not writable: {user_data_dir}")
        except OSError as exc:
            errors.append(f"Cannot access user data directory {user_data_dir}: {exc}")

    # 3. Validate proxy format
    if profile.proxy and profile.proxy.server:
        server = profile.proxy.server.strip()
        allowed_schemes = ("http://", "https://", "socks4://", "socks5://")
        if server and not server.lower().startswith(allowed_schemes):
            errors.append(f"Proxy server must use http://, https://, socks4://, or socks5:// (got: {server})")

    # 4. Validate startup URL
    if profile.startup_url:
        url = profile.startup_url.strip()
        if url and not url.startswith(("http://", "https://", "about:")):
            errors.append(f"Startup URL must start with http://, https://, or about: (got: {url})")

    # 5. Check if profile name is valid
    if not profile.name or not profile.name.strip():
        errors.append("Profile name cannot be empty")

    # 6. Engine constraints (Phase A / C)
    if engine == "chromium" and (profile.mode or "").lower() == "server":
        errors.append("Chromium engine does not support server mode in Phase A (use mode=browser)")
    if engine == "chromium":
        backend = normalize_chromium_backend_name(getattr(profile, "chromium_backend", None))
        if backend == "patchright" and not import_available("patchright"):
            errors.append(
                "patchright is not installed (required for chromium_backend=patchright). "
                f"Run: {chromium_install_hint('patchright')}"
            )
        elif backend == "playwright" and not import_available("playwright"):
            errors.append(
                "playwright is not installed (required for chromium_backend=playwright). "
                f"Run: {chromium_install_hint('playwright')}"
            )
        elif backend == "auto" and not (
            import_available("patchright") or import_available("playwright")
        ):
            errors.append(
                "neither patchright nor playwright is installed (required for chromium). "
                f"Run: {chromium_install_hint('auto')}"
            )
        channel = (getattr(profile, "chromium_channel", None) or "").strip()
        if channel == "chrome" and not detect_google_chrome_install().get("installed"):
            errors.append(
                "chromium_channel=chrome but Google Chrome was not found. "
                "Install Chrome or set channel to empty (bundled Chromium)."
            )
    if engine == "camoufox" and not import_available("camoufox"):
        # Soft: binary check already above; package import still useful
        pass

    # 7. user_data_dir must not be shared across engines (path marker convention)
    ud = (profile.user_data_dir or "").replace("\\", "/").lower()
    if engine == "chromium" and "/camoufox" in ud and "chromium" not in ud:
        errors.append(
            "user_data_dir looks like a camoufox profile path; use a separate directory for chromium "
            "(e.g. .../profiles/<name>-chromium)"
        )
    if engine == "camoufox" and "-chromium" in ud:
        errors.append(
            "user_data_dir looks like a chromium profile path; use a separate directory for camoufox"
        )

    # Phase B consistency hard checks (always)
    sw = int(getattr(profile, "screen_width", 0) or 0)
    sh = int(getattr(profile, "screen_height", 0) or 0)
    if (sw > 0) ^ (sh > 0):
        errors.append("screen_width and screen_height must both be set or both empty")
    ua = (getattr(profile, "user_agent", "") or "").strip()
    if ua and len(ua) < 20:
        errors.append("user_agent looks too short")
    if ua and "HeadlessChrome" in ua:
        errors.append("user_agent must not contain HeadlessChrome")

    # Phase B strict policy: promote high environment risks to launch errors
    policy = (getattr(profile, "consistency_policy", None) or "normal").strip().lower()
    if policy == "strict":
        for risk in environment_risks_for_profile(profile):
            if risk.get("level") == "high":
                errors.append(f"[strict] {risk.get('code')}: {risk.get('message')}")

    return errors


def detect_google_chrome_install() -> dict[str, Any]:
    """Best-effort local Google Chrome path detection (Windows-focused). Not a guarantee."""
    candidates: list[Path] = []
    env_candidates = [
        os.environ.get("PROGRAMFILES", ""),
        os.environ.get("PROGRAMFILES(X86)", ""),
        os.environ.get("LOCALAPPDATA", ""),
    ]
    for root in env_candidates:
        if not root:
            continue
        base = Path(root)
        candidates.extend(
            [
                base / "Google" / "Chrome" / "Application" / "chrome.exe",
                base / "Google" / "Chrome Beta" / "Application" / "chrome.exe",
            ]
        )
    # macOS / Linux common paths (harmless if missing)
    candidates.extend(
        [
            Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            Path("/usr/bin/google-chrome"),
            Path("/usr/bin/google-chrome-stable"),
            Path("/usr/bin/chromium"),
            Path("/usr/bin/chromium-browser"),
        ]
    )
    found: list[str] = []
    for path in candidates:
        try:
            if path.is_file():
                found.append(str(path))
        except OSError:
            continue
    return {"installed": bool(found), "paths": found[:5]}


def environment_risks_for_profile(profile: Profile) -> list[dict[str, str]]:
    """Soft warnings for high-risk site environments (not hard errors).

    These do **not** guarantee pass rates (payment, AI signup/subscribe, etc.).
    """
    risks: list[dict[str, str]] = []

    def add(code: str, level: str, message: str, suggestion: str | None = None) -> None:
        entry = {"code": code, "level": level, "message": message}
        if suggestion:
            entry["suggestion"] = suggestion
        risks.append(entry)

    tags = {str(t).lower() for t in (getattr(profile, "tags", None) or [])}
    ai_scene = bool(tags & {"ai", "chatgpt", "claude", "gemini", "openai", "anthropic"})

    engine = normalize_engine_name(getattr(profile, "engine", None))
    if engine == "chromium":
        backend_req = normalize_chromium_backend_name(getattr(profile, "chromium_backend", None))
        try:
            backend_eff = resolve_chromium_backend(backend_req)
        except Exception:
            backend_eff = backend_req
        if backend_eff == "patchright":
            add(
                "engine_chromium_phase_c_patchright",
                "low",
                "Chromium backend=patchright (Phase C). Improves automation concealment vs stock Playwright; still not a Multilogin-class or signup guarantee.",
            )
        else:
            add(
                "engine_chromium_playwright",
                "medium",
                "Chromium backend=playwright. Automation signals (e.g. webdriver) are more likely; prefer chromium_backend=auto/patchright when installed.",
            )
            if backend_req == "auto" and not import_available("patchright"):
                add(
                    "patchright_not_installed",
                    "medium",
                    "patchright not installed; auto fell back to playwright. Install: pip install patchright && patchright install chromium",
                )
        channel = (getattr(profile, "chromium_channel", None) or "").strip()
        chrome = detect_google_chrome_install()
        if not channel:
            if chrome.get("installed"):
                add(
                    "chromium_bundled_build",
                    "low",
                    "Using bundled Chromium (not channel=chrome). Google Chrome detected on this machine — optional: set chromium_channel=chrome.",
                    suggestion="chromium_channel=chrome",
                )
            else:
                add(
                    "chromium_bundled_build",
                    "low",
                    "Using bundled Chromium build (not channel=chrome). Optional if Chrome is installed later.",
                )
        elif channel == "chrome" and not chrome.get("installed"):
            add(
                "chrome_channel_missing",
                "high",
                "chromium_channel=chrome but Google Chrome was not found in common install paths.",
            )
    else:
        add(
            "engine_firefox_payment_stack",
            "medium",
            "Camoufox is Firefox-based; many Chromium-oriented sites (checkout / some AI flows) score Chromium stacks more leniently.",
        )

    if profile.headless:
        add(
            "headless",
            "high",
            "Headless mode is commonly blocked by payment / 3DS / interactive signup flows. Use a visible browser window.",
        )
    extra_args = list(getattr(profile, "extra_args", None) or [])
    addons = list(getattr(profile, "addons", None) or [])
    if extra_args:
        add(
            "extra_args_present",
            "medium",
            f"extra_args are passed to the browser verbatim ({len(extra_args)} item(s)); review them — some Chromium flags can execute commands or break the fingerprint.",
        )
    if addons:
        add(
            "addons_present",
            "medium",
            f"Addons are loaded from arbitrary paths ({len(addons)} item(s)); only use extensions you trust.",
        )
    if (profile.mode or "").lower() == "server":
        add(
            "server_mode",
            "high",
            "Server mode is for automation endpoints, not interactive signup/subscribe UIs.",
        )
    if ai_scene and engine != "chromium":
        add(
            "ai_scene_prefer_chromium",
            "medium",
            "AI-tagged profile on Camoufox/Firefox. Many users prefer Chromium + patchright for ChatGPT/Claude/Gemini-style flows (still no guarantee).",
        )
    if ai_scene and not profile.persistent_context:
        add(
            "ai_scene_no_persistent",
            "high",
            "AI workstation-style use usually needs persistent_context so cookies/session survive restarts.",
        )
    if profile.block_webgl:
        add(
            "block_webgl",
            "high",
            "Blocking WebGL removes GPU signals many checkout pages expect.",
        )
    if profile.block_images:
        add(
            "block_images",
            "medium",
            "Blocking images can break CAPTCHA / 3DS challenge pages.",
        )
    has_proxy = bool((profile.proxy and profile.proxy.server) or profile.proxy_id)
    if not has_proxy:
        add(
            "no_proxy",
            "medium",
            "No proxy configured. Exit IP will be your real network; payment risk engines often weight IP reputation heavily.",
        )
    if has_proxy and not profile.geoip:
        if engine == "chromium":
            # Chromium worker does not auto-geoip; timezone/locale must be set manually.
            if not (profile.timezone or "").strip() or not (profile.locale or "").strip():
                add(
                    "proxy_without_geoip",
                    "high",
                    "Chromium + proxy without geoip: set timezone and locale to match the exit IP (geoip auto is Camoufox-oriented).",
                )
            else:
                add(
                    "proxy_without_geoip",
                    "low",
                    "Chromium engine ignores Camoufox geoip; timezone/locale are set explicitly (good).",
                )
        else:
            add(
                "proxy_without_geoip",
                "high",
                "Proxy is set but geoip is off — timezone/locale may not match the exit IP (common hard-fail for checkout).",
            )
    if has_proxy and not (profile.timezone or "").strip():
        add(
            "proxy_without_timezone",
            "medium",
            "Proxy without explicit timezone. Prefer a timezone that matches the proxy region (or enable geoip).",
        )
    if has_proxy and not (profile.locale or "").strip():
        add(
            "proxy_without_locale",
            "medium",
            "Proxy without explicit locale/language. Align Accept-Language with the proxy region.",
        )
    # D-B6: exit-IP quality hints from the proxy pool (heuristic ASN/org
    # classification; see backend/proxy_quality.py). Datacenter exits are a
    # top hard-fail cause for payment / AI flows — surface them early.
    if profile.proxy_id:
        try:
            pool_item = proxy_pool.get(profile.proxy_id)
        except KeyError:
            pool_item = None
        quality = (pool_item or {}).get("quality")
        if quality == "datacenter":
            add(
                "datacenter_proxy",
                "medium",
                "Exit IP classified as datacenter/hosting ASN — payment & AI risk engines weight IP reputation heavily and fingerprint work cannot compensate. Prefer a residential/mobile proxy for high-risk flows.",
            )
        elif quality == "residential":
            add(
                "residential_proxy",
                "low",
                "Exit IP classified as residential — good signal for payment / AI flows (heuristic; no guarantee).",
            )
    if not profile.block_webrtc and profile.webrtc_mode == "default":
        add(
            "webrtc_leak_risk",
            "high",
            "WebRTC is not blocked — real local/public IPs may leak beside the proxy.",
        )
    if engine == "chromium" and profile.webrtc_mode == "force_proxy":
        add(
            "webrtc_force_proxy_chromium",
            "medium",
            "Chromium Phase B cannot fully force WebRTC through proxy at kernel level; prefer webrtc_mode=disable + block_webrtc.",
        )
    fonts = list(getattr(profile, "fonts", None) or [])
    font_pack = (getattr(profile, "font_pack", None) or "").strip()
    if engine == "chromium" and not fonts and not font_pack:
        add(
            "fonts_unset",
            "medium",
            "No fonts list / font_pack. Commercial stacks usually pin an OS font set for consistency.",
        )
    # D-B2: JS-layer overrides of Worker-samplable host truths (init scripts
    # never run inside Web Workers; a blob Worker probe reads host values).
    hc_override = int(getattr(profile, "hardware_concurrency", 0) or 0) > 0
    dm_override = float(getattr(profile, "device_memory", 0) or 0) > 0
    if engine == "chromium" and (hc_override or dm_override):
        add(
            "worker_exposed_override",
            "low",
            "hardware_concurrency/device_memory overrides are JS-layer and do not apply inside Web Workers; a blob Worker probe can sample host truth. Prefer leaving these at default (0) unless aligned testing says otherwise.",
        )
    media = (getattr(profile, "media_devices", None) or "default").strip().lower()
    if engine == "chromium" and media == "default":
        add(
            "media_devices_default",
            "low",
            "media_devices=default leaves host enumerateDevices as-is (may be empty or odd on servers). Prefer random for desktop-like.",
        )
    if media == "empty":
        add(
            "media_devices_empty",
            "medium",
            "media_devices=empty is common on headless/VPS fingerprints; unusual for consumer desktop checkout.",
        )
    if not profile.persistent_context:
        add(
            "no_persistent",
            "medium",
            "Non-persistent context looks like a fresh automation profile (no cookies/history warm-up).",
        )
    if engine == "camoufox" and not profile.humanize:
        add(
            "no_humanize",
            "low",
            "Humanize is off; pointer/scroll patterns may look more robotic.",
        )
    if engine == "chromium" and profile.humanize:
        add(
            "humanize_chromium_noop",
            "info",
            "humanize is Camoufox-oriented; Chromium worker does not apply Camoufox humanize.",
        )
    if profile.screen_width and profile.screen_height:
        if profile.screen_width < 1024 or profile.screen_height < 700:
            add(
                "small_viewport",
                "medium",
                f"Viewport {profile.screen_width}x{profile.screen_height} is unusual for desktop checkout.",
            )
    if not (profile.webgl_vendor or "").strip() and not profile.block_webgl:
        add(
            "webgl_unset",
            "low",
            "WebGL vendor/renderer not pinned; Camoufox defaults apply (usually fine, but less reproducible).",
        )
    if (profile.os or "auto") == "auto":
        add(
            "os_auto",
            "low",
            "OS is auto. For payment flows, pin windows/macos to match the proxy and WebGL story.",
        )
    # Locale vs timezone rough consistency (same map as fingerprint-check).
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
        matched = False
        for loc_prefix, tz_prefix in locale_tz_map.items():
            if profile.locale.startswith(loc_prefix) and profile.timezone.startswith(tz_prefix):
                matched = True
                break
        if not matched:
            add(
                "locale_timezone_mismatch",
                "medium",
                f"Locale ({profile.locale}) and timezone ({profile.timezone}) look inconsistent.",
            )

    add(
        "no_guarantee",
        "info",
        "FoxDesk cannot guarantee payment, AI signup/subscribe, or anti-bot pass rates. Internal quality only — not Multilogin/GoLogin SLA.",
    )
    return risks


def pick_proxy_from_pool(profile: Profile) -> dict[str, Any] | None:
    """Resolve proxy according to settings: sticky | round_robin | random_healthy."""
    global _rr_proxy_index
    mode = (settings_store.get().get("proxy_assign_mode") or "sticky").strip().lower()
    items = proxy_pool.all()
    if not items:
        return None

    # Explicit binding always wins for sticky; for other modes still prefer healthy pool.
    if mode == "sticky":
        proxy_id = (profile.proxy_id or "").strip()
        if proxy_id:
            try:
                return proxy_pool.get(proxy_id)
            except KeyError:
                return None
        return None

    healthy = [p for p in items if p.get("last_ok") is True]
    candidates = healthy or items
    if mode == "random_healthy":
        import random

        return random.choice(candidates)
    if mode == "round_robin":
        with _rr_proxy_lock:
            item = candidates[_rr_proxy_index % len(candidates)]
            _rr_proxy_index += 1
            return item
    return None


def apply_proxy_pool_to_profile(profile: Profile) -> Profile:
    item = pick_proxy_from_pool(profile)
    if not item:
        # sticky with no proxy_id: keep manual proxy on profile
        return profile
    data = profile.model_dump()
    data["proxy"] = {
        "server": item.get("server") or "",
        "username": item.get("username") or "",
        "password": item.get("password") or "",
    }
    data["proxy_id"] = item.get("id") or data.get("proxy_id") or ""
    return Profile(**data)
