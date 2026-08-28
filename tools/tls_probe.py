#!/usr/bin/env python3
"""D-B4: TLS / HTTP2 fingerprint leak probe (B-leak, optional manual tool).

Records the JA3 / JA4 / HTTP2 / Akamai fingerprints that the *real Chromium
network stack* (not the JS layer) presents when driven through
Playwright/Patchright, for comparison against a plain browser session.

Key insight being measured: automation stacks do NOT alter TLS — the risk is
**version skew** (automation Chromium trailing the current stable) and
headless-specific ALPN/order differences. Compare outputs across:
  - plain Chrome (same machine, same version)
  - FoxDesk chromium_backend=patchright
  - older bundled Chromium

Usage:
  python tools/tls_probe.py                       # print + save default JSON
  python tools/tls_probe.py --label plain-chrome  # annotate the record
  python tools/tls_probe.py --backend playwright  # compare backends

Uses the public https://tls.peet.ws/api/all echo service (no credentials,
GET only). Output file is gitignored (docs/research/_*.json).
Research aid only — not an anti-detect claim.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TLS_ECHO_URL = "https://tls.peet.ws/api/all"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="FoxDesk TLS/HTTP2 leak probe (D-B4)")
    p.add_argument("--label", default="", help="free-form label stored in the record")
    p.add_argument("--backend", choices=("auto", "playwright", "patchright"), default="auto")
    p.add_argument("--channel", default="")
    p.add_argument("--json-out", default=str(ROOT / "docs" / "research" / "_tls_leak.json"))
    p.add_argument("--url", default=TLS_ECHO_URL, help="TLS echo endpoint")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    from backend.chromium_worker import resolve_sync_playwright

    profile = {"chromium_backend": args.backend}
    try:
        sync_playwright, backend_name = resolve_sync_playwright(profile)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": f"backend import failed: {exc}"}, indent=2))
        return 2

    result: dict = {
        "ok": False,
        "label": args.label,
        "backend": backend_name,
        "channel": args.channel or None,
        "url": args.url,
        "started_at": time.time(),
    }

    import tempfile

    user_data = Path(tempfile.mkdtemp(prefix="foxdesk-tls-"))
    launch_kwargs: dict = {"headless": False, "args": ["--disable-dev-shm-usage"]}
    if args.channel:
        launch_kwargs["channel"] = args.channel

    try:
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(str(user_data), **launch_kwargs)
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(args.url, wait_until="domcontentloaded", timeout=60000)
            data = page.evaluate("() => fetch(location.href, {cache: 'no-store'}).then(r => r.json())")
            context.close()

        tls = data.get("tls") or {}
        http2 = data.get("http2") or {}
        result.update(
            {
                "ok": True,
                "user_agent": data.get("user_agent"),
                "ja3": tls.get("ja3"),
                "ja3_hash": tls.get("ja3_hash"),
                "ja4": tls.get("ja4"),
                "akamai_hash": (http2.get("akamai_fingerprint_hash") or None),
                "http2_sent_frames": {
                    "settings": (http2.get("sent_settings") or None),
                },
                "peetws_summary": {
                    k: data.get(k) for k in ("ip_info", "http_version") if data.get(k) is not None
                },
            }
        )
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"

    result["elapsed_s"] = round(time.time() - result["started_at"], 3)
    out_path = Path(args.json_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
