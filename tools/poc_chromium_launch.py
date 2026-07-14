#!/usr/bin/env python3
"""Phase 0 PoC: launch Chromium via Playwright or Patchright.

Examples:
  python tools/poc_chromium_launch.py --probe
  python tools/poc_chromium_launch.py --headed --proxy socks5://127.0.0.1:1080
  python tools/poc_chromium_launch.py --backend patchright --probe
  python tools/poc_chromium_launch.py --channel chrome --probe --headed

Does not modify FoxDesk profiles. Safe for local research only.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _import_sync_playwright(backend: str):
    backend = (backend or "playwright").strip().lower()
    if backend == "playwright":
        from playwright.sync_api import sync_playwright

        return sync_playwright, "playwright"
    if backend == "patchright":
        try:
            from patchright.sync_api import sync_playwright
        except ImportError as exc:
            raise SystemExit(
                "patchright not installed. Run: pip install patchright && patchright install chromium"
            ) from exc
        return sync_playwright, "patchright"
    raise SystemExit(f"unknown backend: {backend}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="FoxDesk Phase 0 Chromium launch PoC")
    p.add_argument("--backend", choices=("playwright", "patchright"), default="playwright")
    p.add_argument("--channel", default="", help='e.g. "chrome" or "msedge" (Playwright channel)')
    p.add_argument("--headed", action="store_true", help="visible window (recommended for payment research)")
    p.add_argument("--headless", action="store_true", help="force headless (default if not --headed)")
    p.add_argument("--user-data-dir", default="", help="persistent profile dir")
    p.add_argument("--proxy", default="", help="e.g. socks5://host:port or http://host:port")
    p.add_argument("--proxy-user", default="")
    p.add_argument("--proxy-pass", default="")
    p.add_argument("--locale", default="en-US")
    p.add_argument("--timezone", default="America/New_York")
    p.add_argument("--url", default="about:blank")
    p.add_argument("--probe", action="store_true", help="run in-page fingerprint probe")
    p.add_argument("--keep-open", type=float, default=0.0, help="seconds to keep browser open")
    p.add_argument(
        "--browsers-path",
        default="",
        help="set PLAYWRIGHT_BROWSERS_PATH for this process (optional)",
    )
    p.add_argument("--json-out", default="", help="write probe/result JSON to path")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if args.browsers_path:
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = args.browsers_path

    headless = True
    if args.headed:
        headless = False
    if args.headless:
        headless = True

    sync_playwright, backend_name = _import_sync_playwright(args.backend)
    result: dict = {
        "ok": False,
        "backend": backend_name,
        "channel": args.channel or None,
        "headless": headless,
        "locale": args.locale,
        "timezone": args.timezone,
        "proxy": args.proxy or None,
        "started_at": time.time(),
    }

    launch_kwargs: dict = {"headless": headless}
    if args.channel:
        launch_kwargs["channel"] = args.channel

    proxy = None
    if args.proxy.strip():
        proxy = {"server": args.proxy.strip()}
        if args.proxy_user:
            proxy["username"] = args.proxy_user
        if args.proxy_pass:
            proxy["password"] = args.proxy_pass

    context_kwargs: dict = {
        "locale": args.locale,
        "timezone_id": args.timezone,
    }
    if proxy:
        context_kwargs["proxy"] = proxy

    user_data = (args.user_data_dir or "").strip()
    if user_data:
        Path(user_data).mkdir(parents=True, exist_ok=True)

    try:
        with sync_playwright() as p:
            browser = None
            context = None
            if user_data:
                # Persistent profile path (closer to real fingerprint browsers).
                context = p.chromium.launch_persistent_context(
                    user_data,
                    **launch_kwargs,
                    **context_kwargs,
                )
                page = context.pages[0] if context.pages else context.new_page()
            else:
                browser = p.chromium.launch(**launch_kwargs)
                context = browser.new_context(**context_kwargs)
                page = context.new_page()

            page.goto(args.url, wait_until="domcontentloaded", timeout=60000)
            result["href"] = page.url
            result["ok"] = True

            if args.probe:
                from tools.poc_fingerprint_probe import probe_page

                result["probe"] = probe_page(page)

            if args.keep_open > 0:
                time.sleep(args.keep_open)

            if context:
                context.close()
            if browser:
                browser.close()
    except Exception as exc:
        result["ok"] = False
        result["error"] = f"{type(exc).__name__}: {exc}"
        print(json.dumps(result, ensure_ascii=False, indent=2), file=sys.stderr)
        if args.json_out:
            Path(args.json_out).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return 1

    result["elapsed_s"] = round(time.time() - result["started_at"], 3)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    print(text)
    if args.json_out:
        Path(args.json_out).write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
