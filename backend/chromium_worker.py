"""Chromium engine worker (Phase A) — Playwright Chromium.

Control channel matches camoufox_worker: .cmd.jsonl / .result.jsonl
Not a commercial anti-detect stack (see docs/research).
"""

from __future__ import annotations

import json
import os
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


running = True
_page_holder: dict[str, Any] = {"page": None, "context": None, "browser": None}
_cmd_lock = threading.RLock()


def emit(event: str, **payload: Any) -> None:
    print(json.dumps({"event": event, **payload}, ensure_ascii=False), flush=True)


def stop_handler(signum: int, frame: object) -> None:
    global running
    running = False
    emit("signal", signum=signum)


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


def validate_evaluate_expression(expression: str) -> str:
    value = (expression or "").strip()
    if not value:
        raise ValueError("expression is required")
    if len(value) > 1500:
        raise ValueError("expression too long (max 1500 chars)")
    lowered = value.lower()
    for token in (
        "import(",
        "require(",
        "process.",
        "child_process",
        "fs.",
        "__import__",
        "subprocess",
    ):
        if token in lowered:
            raise ValueError(f"expression rejects token: {token}")
    return value


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
      let uaCh = null;
      try {
        if (nav.userAgentData && nav.userAgentData.brands) {
          uaCh = {
            brands: nav.userAgentData.brands,
            mobile: !!nav.userAgentData.mobile,
            platform: nav.userAgentData.platform || '',
          };
        }
      } catch (e) {}
      return {
        engine: 'chromium',
        userAgent: nav.userAgent || '',
        platform: nav.platform || '',
        language: nav.language || '',
        languages: Array.from(nav.languages || []),
        webdriver: !!nav.webdriver,
        hardwareConcurrency: nav.hardwareConcurrency || 0,
        deviceMemory: nav.deviceMemory || 0,
        maxTouchPoints: nav.maxTouchPoints || 0,
        vendor: nav.vendor || '',
        screen: {
          width: screenObj.width || 0,
          height: screenObj.height || 0,
          colorDepth: screenObj.colorDepth || 0,
        },
        timezone,
        webglVendor,
        webglRenderer,
        uaCh,
        href: location.href || '',
        hasChrome: typeof window.chrome === 'object' && window.chrome !== null,
      };
    }
    """
    base = page.evaluate(script)
    # Optional media / fonts probes (async-safe via second evaluate).
    try:
        media = page.evaluate(
            """async () => {
              try {
                if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) {
                  return { count: 0, kinds: [] };
                }
                const devices = await navigator.mediaDevices.enumerateDevices();
                return {
                  count: devices.length,
                  kinds: devices.map((d) => d.kind),
                  labelsSample: devices.slice(0, 5).map((d) => d.label || ''),
                };
              } catch (e) {
                return { error: String(e) };
              }
            }"""
        )
        base["mediaDevices"] = media
    except Exception as exc:
        base["mediaDevices"] = {"error": str(exc)}
    try:
        fonts_check = page.evaluate(
            """() => {
              const samples = ['Arial', 'Segoe UI', 'Times New Roman', 'Helvetica', 'Noto Sans'];
              const out = {};
              for (const name of samples) {
                try {
                  out[name] = !!(document.fonts && document.fonts.check(`16px "${name}"`));
                } catch (e) {
                  out[name] = null;
                }
              }
              return out;
            }"""
        )
        base["fontsCheck"] = fonts_check
    except Exception as exc:
        base["fontsCheck"] = {"error": str(exc)}
    return base


def build_fingerprint_init_script(profile: dict[str, Any]) -> str | None:
    """Phase B best-effort navigator / media / font overrides (not anti-detect)."""
    try:
        from backend.fingerprint_presets import resolve_font_list, resolve_media_devices
    except Exception:
        resolve_font_list = None  # type: ignore
        resolve_media_devices = None  # type: ignore

    platform = (profile.get("navigator_platform") or "").strip()
    vendor = (profile.get("navigator_vendor") or "").strip()
    hc = int(profile.get("hardware_concurrency") or 0)
    dm = float(profile.get("device_memory") or 0)
    mtp = profile.get("max_touch_points", -1)
    try:
        mtp_i = int(mtp)
    except (TypeError, ValueError):
        mtp_i = -1
    ua_ch_platform = (profile.get("ua_ch_platform") or "").strip()
    ua_ch_mobile = bool(profile.get("ua_ch_mobile", False))
    webgl_vendor = (profile.get("webgl_vendor") or "").strip()
    webgl_renderer = (profile.get("webgl_renderer") or "").strip()
    color_depth = int(profile.get("screen_color_depth") or 0)
    dpr = float(profile.get("device_pixel_ratio") or 0)
    fonts: list[str] = []
    if resolve_font_list is not None:
        fonts = resolve_font_list(profile)
    else:
        fonts = [str(f).strip() for f in (profile.get("fonts") or []) if str(f).strip()]
    media_mode = "default"
    media_devices: list[dict[str, str]] | None = None
    if resolve_media_devices is not None:
        media_mode, media_devices = resolve_media_devices(profile)
    else:
        media_mode = (profile.get("media_devices") or "default").strip().lower()

    overrides: dict[str, Any] = {}
    if platform:
        overrides["platform"] = platform
    if vendor:
        overrides["vendor"] = vendor
    if hc > 0:
        overrides["hardwareConcurrency"] = hc
    if dm > 0:
        overrides["deviceMemory"] = dm
    if mtp_i >= 0:
        overrides["maxTouchPoints"] = mtp_i
    # Always provide a desktop-like UA-CH surface on Chromium (config layer, not kernel).
    # Empty platform still gets a Windows default when OS looks windows-like.
    os_name = (profile.get("os") or "").strip().lower()
    if not ua_ch_platform:
        if os_name in {"windows", "win"} or (profile.get("navigator_platform") or "").lower().startswith("win"):
            ua_ch_platform = "Windows"
        elif os_name in {"macos", "mac", "darwin"}:
            ua_ch_platform = "macOS"
        elif os_name == "linux":
            ua_ch_platform = "Linux"
        else:
            ua_ch_platform = "Windows"
    overrides["uaCh"] = {"platform": ua_ch_platform, "mobile": ua_ch_mobile}
    if webgl_vendor:
        overrides["webglVendor"] = webgl_vendor
    if webgl_renderer:
        overrides["webglRenderer"] = webgl_renderer
    if color_depth > 0:
        overrides["colorDepth"] = color_depth
    if dpr > 0:
        overrides["devicePixelRatio"] = dpr
    if fonts:
        overrides["fonts"] = fonts
    if media_mode == "empty":
        overrides["mediaDevices"] = []
    elif media_mode == "random" and media_devices is not None:
        overrides["mediaDevices"] = media_devices
    elif media_mode == "random" and media_devices is None:
        # Fallback desktop set if preset resolver unavailable
        overrides["mediaDevices"] = [
            {
                "deviceId": "default",
                "kind": "audioinput",
                "label": "Default - Microphone Array (Realtek Audio)",
                "groupId": "g-audio-in",
            },
            {
                "deviceId": "default",
                "kind": "audiooutput",
                "label": "Default - Speakers (Realtek Audio)",
                "groupId": "g-audio-out",
            },
            {
                "deviceId": "default",
                "kind": "videoinput",
                "label": "Integrated Camera",
                "groupId": "g-video-in",
            },
        ]

    # Soft chrome runtime presence (commercial stacks almost always expose window.chrome).
    overrides["ensureChrome"] = True

    if len(overrides) <= 1 and not overrides.get("fonts") and "mediaDevices" not in overrides:
        # only ensureChrome — still useful
        pass

    payload = json.dumps(overrides, ensure_ascii=False)
    return f"""
(() => {{
  const o = {payload};
  const def = (obj, key, value) => {{
    try {{
      Object.defineProperty(obj, key, {{ get: () => value, configurable: true }});
    }} catch (e) {{}}
  }};
  try {{
    if (o.platform) def(Navigator.prototype, 'platform', o.platform);
    if (o.vendor) def(Navigator.prototype, 'vendor', o.vendor);
    if (o.hardwareConcurrency) def(Navigator.prototype, 'hardwareConcurrency', o.hardwareConcurrency);
    if (o.deviceMemory) def(Navigator.prototype, 'deviceMemory', o.deviceMemory);
    if (typeof o.maxTouchPoints === 'number') def(Navigator.prototype, 'maxTouchPoints', o.maxTouchPoints);
    if (o.devicePixelRatio) def(window, 'devicePixelRatio', o.devicePixelRatio);
    if (o.colorDepth) {{
      def(Screen.prototype, 'colorDepth', o.colorDepth);
      def(Screen.prototype, 'pixelDepth', o.colorDepth);
    }}
    if (o.ensureChrome && (typeof window.chrome === 'undefined' || window.chrome === null)) {{
      try {{ window.chrome = {{ runtime: {{}} }}; }} catch (e) {{}}
    }}
    // UA-CH: some patched Chromiums strip userAgentData; re-install aggressively.
    try {{
      const ua = String(navigator.userAgent || '');
      let major = '127';
      const m = ua.match(/Chrome\\/(\\d+)/);
      if (m) major = m[1];
      const brands = [
        {{ brand: 'Chromium', version: major }},
        {{ brand: 'Not.A/Brand', version: '24' }},
        {{ brand: 'Google Chrome', version: major }},
      ];
      const platformName = (o.uaCh && o.uaCh.platform) ? o.uaCh.platform : 'Windows';
      const mobileFlag = !!(o.uaCh && o.uaCh.mobile);
      const fullVersion = major + '.0.0.0';
      const data = {{
        brands,
        mobile: mobileFlag,
        platform: platformName,
        getHighEntropyValues: async (hints) => {{
          const out = {{ brands, mobile: mobileFlag, platform: platformName }};
          if (Array.isArray(hints)) {{
            for (const h of hints) {{
              if (h === 'architecture') out.architecture = 'x86';
              if (h === 'bitness') out.bitness = '64';
              if (h === 'model') out.model = '';
              if (h === 'platformVersion') out.platformVersion = platformName === 'Windows' ? '15.0.0' : '14.0.0';
              if (h === 'uaFullVersion') out.uaFullVersion = fullVersion;
              if (h === 'fullVersionList') out.fullVersionList = brands.map((b) => ({{ brand: b.brand, version: fullVersion }}));
            }}
          }}
          return out;
        }},
        toJSON: () => ({{ brands, mobile: mobileFlag, platform: platformName }}),
      }};
      const install = () => {{
        let ok = false;
        try {{
          Object.defineProperty(Navigator.prototype, 'userAgentData', {{
            get: () => data,
            configurable: true,
            enumerable: true,
          }});
          ok = true;
        }} catch (e) {{}}
        try {{
          Object.defineProperty(navigator, 'userAgentData', {{
            get: () => data,
            configurable: true,
            enumerable: true,
          }});
          ok = true;
        }} catch (e) {{}}
        try {{
          // Last resort: direct assignment (may work when defineProperty is blocked).
          navigator.userAgentData = data;
          ok = true;
        }} catch (e) {{}}
        return ok;
      }};
      install();
      try {{ setTimeout(install, 0); }} catch (e) {{}}
    }} catch (e) {{}}
    if (o.webglVendor || o.webglRenderer) {{
      const patch = (proto) => {{
        if (!proto || !proto.getParameter) return;
        const original = proto.getParameter;
        proto.getParameter = function(param) {{
          const dbg = this.getExtension && this.getExtension('WEBGL_debug_renderer_info');
          if (dbg) {{
            if (o.webglVendor && param === dbg.UNMASKED_VENDOR_WEBGL) return o.webglVendor;
            if (o.webglRenderer && param === dbg.UNMASKED_RENDERER_WEBGL) return o.webglRenderer;
          }}
          return original.apply(this, arguments);
        }};
      }};
      try {{
        const c = document.createElement('canvas');
        const gl = c.getContext('webgl') || c.getContext('experimental-webgl');
        if (gl) patch(Object.getPrototypeOf(gl));
      }} catch (e) {{}}
    }}
    if (Array.isArray(o.mediaDevices)) {{
      try {{
        const list = o.mediaDevices.map((d) => Object.assign({{
          deviceId: d.deviceId || 'default',
          kind: d.kind || 'audioinput',
          label: d.label || '',
          groupId: d.groupId || 'group',
          toJSON: function() {{ return {{ deviceId: this.deviceId, kind: this.kind, label: this.label, groupId: this.groupId }}; }}
        }}, d));
        const enumerate = async () => list.map((x) => Object.assign({{}}, x));
        const patchMd = (md) => {{
          if (!md) return;
          try {{ md.enumerateDevices = enumerate; }} catch (e) {{}}
          try {{
            Object.defineProperty(md, 'enumerateDevices', {{ value: enumerate, configurable: true, writable: true }});
          }} catch (e) {{}}
        }};
        const fake = {{
          enumerateDevices: enumerate,
          getUserMedia: async () => {{ throw new DOMException('Permission denied', 'NotAllowedError'); }},
          getSupportedConstraints: () => ({{ audio: true, video: true }}),
          addEventListener: () => {{}},
          removeEventListener: () => {{}},
          dispatchEvent: () => false,
        }};
        try {{ def(Navigator.prototype, 'mediaDevices', fake); }} catch (e) {{}}
        try {{
          if (navigator.mediaDevices) patchMd(navigator.mediaDevices);
          else Object.defineProperty(navigator, 'mediaDevices', {{ get: () => fake, configurable: true }});
        }} catch (e2) {{
          try {{ Object.defineProperty(navigator, 'mediaDevices', {{ get: () => fake, configurable: true }}); }} catch (e3) {{}}
        }}
        // Re-apply after a tick (some engines reset mediaDevices late).
        try {{ setTimeout(() => {{ try {{ patchMd(navigator.mediaDevices); }} catch (e) {{}} }}, 0); }} catch (e) {{}}
      }} catch (e) {{}}
    }}
    if (Array.isArray(o.fonts) && o.fonts.length) {{
      // Best-effort font presence probe surface for scripts that use document.fonts.check
      try {{
        const allowed = new Set(o.fonts.map((f) => String(f).toLowerCase()));
        if (document.fonts && document.fonts.check) {{
          const original = document.fonts.check.bind(document.fonts);
          document.fonts.check = function(font, text) {{
            try {{
              const family = String(font || '').replace(/^[^\"']*[\"']?|[\"']?$/g, '').toLowerCase();
              // If a listed family is requested, claim available; else fall through.
              for (const name of allowed) {{
                if (String(font || '').toLowerCase().includes(name)) return true;
              }}
            }} catch (e) {{}}
            return original(font, text);
          }};
        }}
      }} catch (e) {{}}
    }}
  }} catch (e) {{}}
}})();
"""


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
                reply(ok=False, error="no active page")
                return
            url = validate_nav_url(str(cmd.get("url") or ""))
            emit("navigate", url=url, request_id=req_id)
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            reply(ok=True, url=url, href=getattr(page, "url", url))
            return
        if action in {"fingerprint", "fingerprint_probe", "probe"}:
            if page is None:
                reply(ok=False, error="no active page")
                return
            data = probe_fingerprint(page)
            reply(ok=True, report=data)
            return
        if action in {"screenshot", "shot"}:
            if page is None:
                reply(ok=False, error="no active page")
                return
            import base64

            full_page = bool(cmd.get("full_page"))
            raw = page.screenshot(type="png", full_page=full_page)
            if not isinstance(raw, (bytes, bytearray)):
                reply(ok=False, error="screenshot returned non-bytes")
                return
            if len(raw) > 4 * 1024 * 1024:
                reply(ok=False, error=f"screenshot too large ({len(raw)} bytes)")
                return
            reply(
                ok=True,
                mime="image/png",
                full_page=full_page,
                size=len(raw),
                image_base64=base64.b64encode(bytes(raw)).decode("ascii"),
                href=getattr(page, "url", None),
            )
            return
        if action in {"evaluate", "eval"}:
            if page is None:
                reply(ok=False, error="no active page")
                return
            expression = validate_evaluate_expression(
                str(cmd.get("expression") or cmd.get("script") or "")
            )
            value = page.evaluate(f"() => ({expression})")
            try:
                json.dumps(value)
            except TypeError as exc:
                reply(ok=False, error=f"result not JSON-serializable: {exc}")
                return
            reply(ok=True, value=value, href=getattr(page, "url", None))
            return
        if action == "ping":
            reply(ok=True, ready=page is not None, engine="chromium")
            return
        reply(ok=False, error=f"unknown command: {action}")
    except Exception as exc:
        reply(ok=False, error=str(exc))


def command_loop(profile_path: Path) -> None:
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


def resolve_sync_playwright(profile: dict[str, Any]):
    """Phase C: pick patchright or playwright sync API.

    Returns (sync_playwright_factory, backend_name).
    """
    requested = (profile.get("chromium_backend") or "auto").strip().lower()
    if requested in {"", "default"}:
        requested = "auto"
    if requested in {"pw"}:
        requested = "playwright"
    if requested in {"pr", "patched"}:
        requested = "patchright"

    def _load_patchright():
        from patchright.sync_api import sync_playwright

        return sync_playwright, "patchright"

    def _load_playwright():
        from playwright.sync_api import sync_playwright

        return sync_playwright, "playwright"

    errors: list[str] = []
    if requested == "patchright":
        try:
            return _load_patchright()
        except Exception as exc:
            raise RuntimeError(f"patchright import failed: {exc}") from exc
    if requested == "playwright":
        try:
            return _load_playwright()
        except Exception as exc:
            raise RuntimeError(f"playwright import failed: {exc}") from exc
    # auto: prefer patchright
    try:
        return _load_patchright()
    except Exception as exc:
        errors.append(f"patchright: {exc}")
    try:
        return _load_playwright()
    except Exception as exc:
        errors.append(f"playwright: {exc}")
    raise RuntimeError("no chromium backend available: " + "; ".join(errors))


def run_browser(profile: dict[str, Any], profile_path: Path) -> int:
    global running
    # Prefer product browsers dir when present (Phase A packaging path).
    browsers_dir = os.environ.get("FOXDESK_BROWSERS_PATH") or os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if not browsers_dir:
        # Common FoxDesk data layout when launched from manager.
        appdata = os.environ.get("APPDATA") or ""
        candidate = Path(appdata) / "FoxDesk" / "browsers" if appdata else None
        if candidate and candidate.exists():
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(candidate)

    try:
        sync_playwright, backend_name = resolve_sync_playwright(profile)
    except Exception as exc:
        msg = f"failed to import chromium backend: {exc}"
        low = str(exc).lower()
        if "patchright" in low:
            msg += " | Install: pip install patchright && patchright install chromium"
        elif "playwright" in low:
            msg += " | Install: pip install playwright && playwright install chromium"
        else:
            msg += (
                " | Install: pip install playwright patchright && "
                "playwright install chromium && patchright install chromium"
            )
        emit("error", message=msg, backend=(profile.get("chromium_backend") or "auto"))
        return 2

    headless = bool(profile.get("headless", False))
    locale = (profile.get("locale") or "").strip() or None
    timezone = (profile.get("timezone") or "").strip() or None
    proxy = build_proxy(profile)
    startup_url = (profile.get("startup_url") or "").strip() or "about:blank"
    user_data_dir = (profile.get("user_data_dir") or "").strip()
    channel = (profile.get("chromium_channel") or "").strip() or None
    width = int(profile.get("screen_width") or 0)
    height = int(profile.get("screen_height") or 0)
    user_agent = (profile.get("user_agent") or "").strip() or None
    init_script = build_fingerprint_init_script(profile)

    launch_kwargs: dict[str, Any] = {"headless": headless}
    if channel:
        launch_kwargs["channel"] = channel
    # Soften some automation defaults (not a commercial anti-detect stack).
    launch_kwargs["args"] = list(profile.get("extra_args") or [])
    soft_flags = [
        "--disable-blink-features=AutomationControlled",
        "--disable-dev-shm-usage",
    ]
    webrtc_mode = (profile.get("webrtc_mode") or "default").strip().lower()
    if profile.get("block_webrtc") or webrtc_mode == "disable":
        # Best-effort WebRTC suppress (not kernel-grade proxy force).
        soft_flags.extend(
            [
                "--enforce-webrtc-ip-permission-check",
                "--disable-features=WebRtcHideLocalIpsWithMdns",
                "--force-webrtc-ip-handling-policy=disable_non_proxied_udp",
            ]
        )
    for flag in soft_flags:
        if flag not in launch_kwargs["args"]:
            launch_kwargs["args"].append(flag)

    context_kwargs: dict[str, Any] = {}
    if locale:
        context_kwargs["locale"] = locale
    if timezone:
        context_kwargs["timezone_id"] = timezone
    if proxy:
        context_kwargs["proxy"] = proxy
    if width > 0 and height > 0:
        context_kwargs["viewport"] = {"width": width, "height": height}
    if user_agent:
        context_kwargs["user_agent"] = user_agent
    if profile.get("device_pixel_ratio"):
        try:
            dpr = float(profile.get("device_pixel_ratio") or 0)
            if dpr > 0:
                context_kwargs["device_scale_factor"] = dpr
        except (TypeError, ValueError):
            pass
    # Reduce Playwright default "automation" chrome bits where supported.
    context_kwargs.setdefault("ignore_https_errors", False)

    emit(
        "launching",
        engine="chromium",
        backend=backend_name,
        headless=headless,
        proxy=proxy.get("server") if proxy else None,
        locale=locale,
        timezone=timezone,
        channel=channel,
        has_init_script=bool(init_script),
        user_agent=bool(user_agent),
    )

    cmd_thread = threading.Thread(target=command_loop, args=(profile_path,), daemon=True)
    cmd_thread.start()

    browser = None
    context = None
    try:
        with sync_playwright() as p:
            if profile.get("persistent_context", True) and user_data_dir:
                path = Path(user_data_dir).expanduser()
                path.mkdir(parents=True, exist_ok=True)
                context = p.chromium.launch_persistent_context(
                    str(path),
                    **launch_kwargs,
                    **context_kwargs,
                )
                page = context.pages[0] if context.pages else context.new_page()
            else:
                browser = p.chromium.launch(**launch_kwargs)
                context = browser.new_context(**context_kwargs)
                page = context.new_page()

            if init_script:
                try:
                    context.add_init_script(init_script)
                    emit("fingerprint_init", applied=True)
                except Exception as exc:
                    emit("warning", message=f"init script failed: {exc}")

            _page_holder["browser"] = browser
            _page_holder["context"] = context
            _page_holder["page"] = page

            emit("ready", engine="chromium", backend=backend_name, mode="browser")
            try:
                # Navigate after init script registration so first document sees overrides.
                page.goto(startup_url, wait_until="domcontentloaded", timeout=60000)
                emit("navigated", url=startup_url, href=page.url)
            except Exception as exc:
                emit("warning", message=f"startup navigation failed: {exc}")

            if profile.get("_auto_fingerprint_probe"):
                try:
                    report = probe_fingerprint(page)
                    emit("fingerprint_report", report=report)
                except Exception as exc:
                    emit("warning", message=f"auto fingerprint probe failed: {exc}")

            while running:
                time.sleep(0.4)
                # Exit if browser/context died.
                try:
                    if browser is not None and not browser.is_connected():
                        break
                except Exception:
                    break
    except Exception as exc:
        text = str(exc)
        low = text.lower()
        hint = ""
        if any(
            k in low
            for k in (
                "executable doesn't exist",
                "browser not found",
                "browsers are not installed",
                "please run the following command to download",
                "chromium distribution is not found",
            )
        ):
            if backend_name == "patchright":
                hint = " | Fix: patchright install chromium"
            else:
                hint = " | Fix: playwright install chromium"
        elif "channel" in low and "chrome" in low:
            hint = " | Fix: install Google Chrome or clear chromium_channel"
        emit(
            "error",
            message=f"chromium launch failed: {text}{hint}",
            backend=backend_name,
            channel=channel,
        )
        return 1
    finally:
        running = False
        _page_holder["page"] = None
        try:
            if context is not None:
                context.close()
        except Exception:
            pass
        try:
            if browser is not None:
                browser.close()
        except Exception:
            pass
        emit("stopped", engine="chromium", backend=backend_name)
    return 0


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: chromium_worker.py <runtime-profile.json>", file=sys.stderr)
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

    mode = (profile.get("mode") or "browser").strip().lower()
    if mode == "server":
        emit("error", message="chromium engine does not support server mode in Phase A")
        return 3
    return run_browser(profile, profile_path)


if __name__ == "__main__":
    raise SystemExit(main())
