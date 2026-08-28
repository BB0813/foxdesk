#!/usr/bin/env python3
"""B-static probe — local static fingerprint checklist for Phase B/C gate.

Runs headed Chromium (Playwright or Patchright) with Phase-B-like profile
overrides (via chromium_worker init script logic) and scores signals against a
commercial-style desktop baseline. Does **not** claim anti-detect or payment success.

Examples:
  python tools/bstatic_probe.py
  python tools/bstatic_probe.py --json-out docs/research/_bstatic_run.json
  python tools/bstatic_probe.py --backend patchright --require-webdriver-false
  python tools/bstatic_probe.py --channel chrome --headed
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="FoxDesk B-static probe (Phase B/C)")
    p.add_argument("--headed", action="store_true", default=True)
    p.add_argument("--headless", action="store_true")
    p.add_argument("--channel", default="")
    p.add_argument(
        "--backend",
        choices=("auto", "playwright", "patchright"),
        default="auto",
        help="Chromium automation backend (Phase C)",
    )
    p.add_argument("--json-out", default=str(ROOT / "docs" / "research" / "_bstatic_run.json"))
    p.add_argument("--keep-open", type=float, default=0.5)
    p.add_argument(
        "--require-webdriver-false",
        action="store_true",
        help="Phase C gate: fail if navigator.webdriver is true",
    )
    return p.parse_args()


def score_probe(probe: dict) -> dict:
    """Score against commercial-desktop-like expectations (config layer only)."""
    checks = []

    def add(code: str, ok: bool, detail: str, severity: str = "medium") -> None:
        checks.append({"code": code, "ok": ok, "detail": detail, "severity": severity})

    ua = str(probe.get("userAgent") or "")
    add("no_headless_ua", "HeadlessChrome" not in ua, f"ua={ua[:80]}", "high")
    add("webdriver_false", probe.get("webdriver") is False, f"webdriver={probe.get('webdriver')}", "high")
    add("has_chrome_runtime", bool(probe.get("hasChromeRuntime") or probe.get("hasChrome")), "window.chrome", "medium")
    add("platform_set", bool(probe.get("platform")), f"platform={probe.get('platform')}", "low")
    add("languages_set", bool(probe.get("languages")), f"languages={probe.get('languages')}", "low")
    add("timezone_set", bool(probe.get("timezone")), f"timezone={probe.get('timezone')}", "medium")
    ua_ch = probe.get("uaChBrands") or (probe.get("uaCh") or {}).get("brands") if isinstance(probe.get("uaCh"), dict) else probe.get("uaChBrands")
    add("ua_ch_present", bool(ua_ch), f"uaCh={ua_ch}", "medium")
    media = probe.get("mediaDevices") or {}
    mcount = int(media.get("count") or 0) if isinstance(media, dict) else 0
    add("media_devices_nonempty", mcount > 0, f"media.count={mcount}", "low")
    fonts = probe.get("fontsCheck") or {}
    font_hits = sum(1 for v in fonts.values() if v is True) if isinstance(fonts, dict) else 0
    add("fonts_some_present", font_hits > 0, f"font_hits={font_hits}", "low")
    plugins = int(probe.get("pluginsLength") or 0)
    add("plugins_nonempty", plugins > 0, f"pluginsLength={plugins}", "low")

    # D-B1 / D-B2 deep probes (Phase D research; measured, never gated)
    deep = probe.get("deep") if isinstance(probe.get("deep"), dict) else {}
    cdp = deep.get("cdp_console_tostring")
    add(
        "cdp_runtime_no_leak",
        cdp is True,
        "console.debug toString trick: hits>0 means a Runtime.enable-style CDP leak",
        "medium",
    )
    iframe = deep.get("iframe_srcdoc_consistent")
    add(
        "iframe_srcdoc_consistent",
        iframe is True,
        "srcdoc iframe navigator matches main frame (init-script coverage)",
        "medium",
    )
    worker = deep.get("worker_consistent")
    add(
        "worker_consistent",
        worker is True,
        "Worker-scope navigator values match main frame",
        "medium",
    )

    high_fail = [c for c in checks if not c["ok"] and c["severity"] == "high"]
    med_fail = [c for c in checks if not c["ok"] and c["severity"] == "medium"]
    passed = sum(1 for c in checks if c["ok"])
    # Phase B gate: config-layer checks; webdriver high-fail is expected until Phase C
    phase_b_blockers = [c for c in high_fail if c["code"] != "webdriver_false"]
    return {
        "checks": checks,
        "passed": passed,
        "total": len(checks),
        "high_fail": high_fail,
        "medium_fail": med_fail,
        "phase_b_gate_ok": len(phase_b_blockers) == 0,
        "phase_c_needed": any(c["code"] == "webdriver_false" and not c["ok"] for c in checks),
        "note": "phase_b_gate ignores webdriver (Phase C). No payment guarantee.",
    }


def probe_deep(page) -> dict:
    """D-B1 (CDP traces) + D-B2 (iframe/Worker consistency) probes.

    Each key is True when no leak/mismatch was found, False when the
    detection surface reports a problem, None when the probe could not run.
    Research measurements only — not an anti-detect claim.
    """
    deep: dict = {}
    # D-B1: Runtime.enable-style CDP leak. With Runtime.enable active the
    # CDP agent deep-serializes console.debug arguments, invoking toString.
    # A real Chrome (or patchright with Runtime.enable held back) reports 0.
    try:
        deep["cdp_console_tostring"] = page.evaluate(
            """async () => {
              let hits = 0;
              const spooky = { toString() { hits += 1; return 'spooky'; } };
              try { console.debug(spooky); } catch (e) {}
              try { console.log(spooky); } catch (e) {}
              await new Promise(r => setTimeout(r, 250));
              return hits === 0;
            }"""
        )
    except Exception:
        deep["cdp_console_tostring"] = None
    # D-B2a: srcdoc iframe realm. Known Chromium gap: init scripts may not
    # run inside srcdoc/sandbox iframes, leaving a fresh navigator realm
    # that detection suites compare against the main frame.
    try:
        deep["iframe_srcdoc_consistent"] = page.evaluate(
            """async () => {
              const iframe = document.createElement('iframe');
              iframe.srcdoc = 'page intentionally left blank';
              iframe.style.display = 'none';
              document.body.appendChild(iframe);
              try {
                await new Promise(r => {
                  let done = false;
                  iframe.onload = () => { done = true; r(); };
                  setTimeout(() => { if (!done) r(); }, 1500);
                });
                const w = iframe.contentWindow;
                if (!w || !w.navigator) return null;
                const main = navigator;
                const inner = w.navigator;
                const keys = ['webdriver', 'hardwareConcurrency', 'userAgent', 'platform'];
                for (const k of keys) {
                  let a, b;
                  try { a = String(main[k]); } catch (e) { a = 'undef'; }
                  try { b = String(inner[k]); } catch (e) { b = 'undef'; }
                  if (a !== b) return false;
                }
                const mUad = main.userAgentData ? String(main.userAgentData.platform) : '';
                const iUad = inner.userAgentData ? String(inner.userAgentData.platform) : '';
                if (mUad !== iUad) return false;
                return true;
              } finally {
                iframe.remove();
              }
            }"""
        )
    except Exception:
        deep["iframe_srcdoc_consistent"] = None
    # D-B2b: dedicated Worker realm. Init scripts never run inside workers;
    # spoofed main-frame values that the host cannot back (e.g. overridden
    # hardwareConcurrency/userAgent) diverge here.
    try:
        deep["worker_consistent"] = page.evaluate(
            """async () => {
              const src = `self.onmessage = () => self.postMessage({
                ua: navigator.userAgent,
                hc: navigator.hardwareConcurrency,
                plat: String(navigator.platform),
              });`;
              const blob = new Blob([src], { type: 'application/javascript' });
              const url = URL.createObjectURL(blob);
              const worker = new Worker(url);
              const data = await new Promise((resolve) => {
                worker.onmessage = (e) => resolve(e.data);
                worker.postMessage('go');
                setTimeout(() => resolve(null), 2000);
              });
              worker.terminate();
              URL.revokeObjectURL(url);
              if (!data) return null;
              const main = navigator;
              return (
                String(data.ua) === String(main.userAgent) &&
                String(data.plat) === String(main.platform)
              );
            }"""
        )
    except Exception:
        deep["worker_consistent"] = None
    return deep


def main() -> int:
    args = parse_args()
    headless = bool(args.headless)
    if args.headed and not args.headless:
        headless = False

    from backend.fingerprint_presets import commercial_windows_desktop_hints
    from backend.chromium_worker import build_fingerprint_init_script, resolve_sync_playwright
    from tools.poc_fingerprint_probe import probe_page

    profile = commercial_windows_desktop_hints()
    profile.update(
        {
            "locale": "en-US",
            "timezone": "America/New_York",
            "chromium_backend": args.backend,
            "user_agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"
            ),
            "webgl_vendor": "Google Inc. (Intel)",
            "webgl_renderer": "ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0)",
        }
    )
    init_script = build_fingerprint_init_script(profile)

    result: dict = {
        "ok": False,
        "headless": headless,
        "channel": args.channel or None,
        "backend_requested": args.backend,
        "profile_keys": sorted(profile.keys()),
        "started_at": time.time(),
    }

    try:
        sync_playwright, backend_name = resolve_sync_playwright(profile)
        result["backend"] = backend_name
    except Exception as exc:
        result["error"] = f"chromium backend import failed: {exc}"
        Path(args.json_out).write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result, indent=2))
        return 2

    user_data = Path(tempfile.mkdtemp(prefix="foxdesk-bstatic-"))
    launch_kwargs: dict = {
        "headless": headless,
        "args": [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--enforce-webrtc-ip-permission-check",
            "--force-webrtc-ip-handling-policy=disable_non_proxied_udp",
        ],
    }
    if args.channel:
        launch_kwargs["channel"] = args.channel

    context_kwargs = {
        "locale": profile["locale"],
        "timezone_id": profile["timezone"],
        "viewport": {"width": profile["screen_width"], "height": profile["screen_height"]},
        "user_agent": profile["user_agent"],
        "device_scale_factor": profile.get("device_pixel_ratio") or 1.0,
    }

    try:
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                str(user_data),
                **launch_kwargs,
                **context_kwargs,
            )
            if init_script:
                context.add_init_script(init_script)
            page = context.pages[0] if context.pages else context.new_page()
            # about:blank often lacks userAgentData; probe on a real https origin
            # (still local research — example.com is inert).
            probe_url = "https://example.com/"
            page.goto(probe_url, wait_until="domcontentloaded", timeout=60000)
            # Second navigation so late init / media hooks settle.
            page.goto(probe_url, wait_until="domcontentloaded", timeout=60000)
            result["probe_url"] = probe_url
            probe = probe_page(page)
            # Enrich with media/fonts like chromium_worker probe
            try:
                probe["mediaDevices"] = page.evaluate(
                    """async () => {
                      if (!navigator.mediaDevices?.enumerateDevices) return { count: 0 };
                      const devices = await navigator.mediaDevices.enumerateDevices();
                      return { count: devices.length, kinds: devices.map(d => d.kind) };
                    }"""
                )
            except Exception as exc:
                probe["mediaDevices"] = {"error": str(exc)}
            try:
                probe["fontsCheck"] = page.evaluate(
                    """() => {
                      const samples = ['Arial','Segoe UI','Times New Roman','Helvetica'];
                      const out = {};
                      for (const n of samples) {
                        try { out[n] = !!(document.fonts && document.fonts.check(`16px "${n}"`)); }
                        catch (e) { out[n] = null; }
                      }
                      return out;
                    }"""
                )
            except Exception as exc:
                probe["fontsCheck"] = {"error": str(exc)}
            probe["hasChrome"] = page.evaluate("() => typeof window.chrome === 'object' && window.chrome !== null")
            probe["deep"] = probe_deep(page)
            result["probe"] = probe
            result["score"] = score_probe(probe)
            result["ok"] = True
            if args.keep_open > 0:
                time.sleep(args.keep_open)
            context.close()
    except Exception as exc:
        result["ok"] = False
        result["error"] = f"{type(exc).__name__}: {exc}"

    result["elapsed_s"] = round(time.time() - result["started_at"], 3)
    out_path = Path(args.json_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    out_path.write_text(text, encoding="utf-8")
    print(text)
    if not result.get("ok"):
        return 1
    score = result.get("score") or {}
    # Exit 0 even if webdriver fails (Phase B); fail only if phase_b_gate fails
    if not score.get("phase_b_gate_ok", False):
        return 3
    if args.require_webdriver_false and score.get("phase_c_needed"):
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
