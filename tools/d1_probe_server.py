#!/usr/bin/env python3
"""D1 compare harness: run the FoxDesk probe set inside ANY browser.

Serves a self-contained probe page on loopback. Open it in the browser
under test (e.g. a Multilogin Mimic profile) — the page runs the same
checks as tools/bstatic_probe.py (basic statics + D-B1/D-B2/D-B3 deep
probes) and POSTs the results back; the server stores them as
docs/research/_d1_<label>.json.

Why this shape: Multilogin automation/API requires a paid plan and
account-bound GUI launch, but a GUI-opened local page needs nothing.
Same JS, same scoring semantics → apples-to-apples against
`python tools/bstatic_probe.py` runs.

Usage:
  python tools/d1_probe_server.py --label mimic-142
  # then open http://127.0.0.1:8807/probe in the target browser,
  # results auto-upload; Ctrl+C to stop.

Research aid only — no anti-detect claims, no guarantees.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PROBE_HTML = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>FoxDesk D1 probe</title>
<style>
  body { font-family: Consolas, monospace; background: #0a0e17; color: #9fd3e8; padding: 24px; }
  .ok { color: #4ade80; } .bad { color: #f87171; } .na { color: #facc15; }
  pre { white-space: pre-wrap; }
</style>
</head>
<body>
<h3>FoxDesk D1 probe — running, will auto-upload…</h3>
<pre id="out">running…</pre>
<script>
const out = document.getElementById('out');
const log = (line) => { out.textContent += line + "\\n"; };

async function basicProbe() {
  const nav = navigator;
  const res = {
    kind: 'basic',
    collected_at: new Date().toISOString(),
    userAgent: nav.userAgent,
    webdriver: nav.webdriver === true,
    hasChrome: (typeof window.chrome === 'object' && window.chrome !== null),
    platform: nav.platform || '',
    languages: (nav.languages || []).join(','),
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || '',
    hardwareConcurrency: nav.hardwareConcurrency || 0,
    deviceMemory: nav.deviceMemory || 0,
    maxTouchPoints: nav.maxTouchPoints ?? -1,
    pluginsLength: nav.plugins ? nav.plugins.length : -1,
  };
  try {
    const md = await nav.mediaDevices.enumerateDevices();
    res.mediaCount = md.length;
    res.mediaKinds = md.map(d => d.kind);
  } catch (e) { res.mediaCount = -1; }
  try {
    const fonts = ['Arial','Segoe UI','Times New Roman','Helvetica','SimSun','Microsoft YaHei'];
    const fc = {};
    for (const n of fonts) { try { fc[n] = !!(document.fonts && document.fonts.check('16px "' + n + '"')); } catch (e) { fc[n] = null; } }
    res.fontsCheck = fc;
  } catch (e) {}
  try {
    if (nav.userAgentData) {
      const h = await nav.userAgentData.getHighEntropyValues(['platform','platformVersion','architecture','bitness','uaFullVersion','fullVersionList','model']);
      res.uaCh = h;
    } else { res.uaCh = null; }
  } catch (e) { res.uaCh = null; }
  try { res.notificationPermission = ('Notification' in window) ? Notification.permission : 'absent'; } catch (e) { res.notificationPermission = 'err'; }
  try {
    const st = await nav.permissions.query({ name: 'notifications' });
    res.notificationsQueryState = st.state;
  } catch (e) { res.notificationsQueryState = 'err'; }
  return res;
}

// D-B1: Runtime.enable-style CDP leak (console.debug toString trick).
async function cdpProbe() {
  try {
    let hits = 0;
    const spooky = { toString() { hits += 1; return 'spooky'; } };
    try { console.debug(spooky); } catch (e) {}
    try { console.log(spooky); } catch (e) {}
    await new Promise(r => setTimeout(r, 250));
    return hits === 0;
  } catch (e) { return null; }
}

// D-B2a: srcdoc iframe realm consistency.
async function iframeProbe() {
  try {
    const iframe = document.createElement('iframe');
    iframe.srcdoc = 'page intentionally left blank';
    iframe.style.display = 'none';
    document.body.appendChild(iframe);
    await new Promise(r => { let done = false; iframe.onload = () => { done = true; r(); }; setTimeout(() => { if (!done) r(); }, 1500); });
    const w = iframe.contentWindow;
    if (!w || !w.navigator) { iframe.remove(); return null; }
    const keys = ['webdriver', 'hardwareConcurrency', 'userAgent', 'platform'];
    for (const k of keys) {
      let a, b;
      try { a = String(navigator[k]); } catch (e) { a = 'undef'; }
      try { b = String(w.navigator[k]); } catch (e) { b = 'undef'; }
      if (a !== b) { iframe.remove(); return false; }
    }
    const mUad = navigator.userAgentData ? String(navigator.userAgentData.platform) : '';
    const iUad = w.navigator.userAgentData ? String(w.navigator.userAgentData.platform) : '';
    iframe.remove();
    return mUad === iUad;
  } catch (e) { return null; }
}

// D-B2b: dedicated Worker realm consistency.
async function workerProbe() {
  try {
    const src = `self.onmessage = () => self.postMessage({ ua: navigator.userAgent, plat: String(navigator.platform) });`;
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
    return String(data.ua) === String(navigator.userAgent) && String(data.plat) === String(navigator.platform);
  } catch (e) { return null; }
}

async function main() {
  const basic = await basicProbe();
  const deep = {
    cdp_console_tostring: await cdpProbe(),
    iframe_srcdoc_consistent: await iframeProbe(),
    worker_consistent: await workerProbe(),
  };
  const payload = { kind: 'd1-report', basic, deep, href: location.href };
  const resp = await fetch('/report', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const ack = await resp.json();
  log('uploaded: ' + JSON.stringify(ack));
  log('webdriver: ' + basic.webdriver + '  hasChrome: ' + basic.hasChrome);
  log('deep: ' + JSON.stringify(deep));
  log('notification: ' + basic.notificationPermission + ' / query: ' + basic.notificationsQueryState);
  log('UA: ' + basic.userAgent);
  log('DONE — you can close this tab.');
}
main().catch(e => log('ERROR: ' + e));
</script>
</body>
</html>
"""


class ProbeHandler(BaseHTTPRequestHandler):
    out_path: Path = None  # type: ignore[assignment]
    label: str = ""

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path.startswith("/probe") or self.path == "/":
            self._send(200, PROBE_HTML.encode("utf-8"), "text/html; charset=utf-8")
        else:
            self._send(404, b"not found", "text/plain")

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/report":
            self._send(404, b"not found", "text/plain")
            return
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            report = json.loads(raw.decode("utf-8", errors="replace"))
        except Exception:
            report = {"raw": raw.decode("utf-8", errors="replace")}
        record = {
            "label": self.label,
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "report": report,
        }
        self.out_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n[D1] report saved -> {self.out_path}", flush=True)
        basic = report.get("basic") or {}
        print(f"[D1] webdriver={basic.get('webdriver')} hasChrome={basic.get('hasChrome')} "
              f"ua={str(basic.get('userAgent'))[:80]}", flush=True)
        print(f"[D1] deep={json.dumps(report.get('deep'))}", flush=True)
        self._send(200, json.dumps({"ok": True, "saved": str(self.out_path)}).encode(), "application/json")

    def log_message(self, fmt: str, *args) -> None:  # silence default noise
        return


def main() -> int:
    parser = argparse.ArgumentParser(description="FoxDesk D1 compare probe server")
    parser.add_argument("--port", type=int, default=8807)
    parser.add_argument("--label", default="d1-target", help="e.g. mimic-142 / stealthfox-144 / plain-chrome")
    parser.add_argument(
        "--out",
        default=str(ROOT / "docs" / "research" / "_d1_target.json"),
        help="output JSON path (label default: _d1_<label>.json)",
    )
    args = parser.parse_args()

    out = Path(args.out)
    if out.name == "_d1_target.json" and args.label != "d1-target":
        out = out.with_name(f"_d1_{args.label}.json")
    ProbeHandler.out_path = out
    ProbeHandler.label = args.label

    server = ThreadingHTTPServer(("127.0.0.1", args.port), ProbeHandler)
    print(f"[D1] probe page: http://127.0.0.1:{args.port}/probe  (open it in the browser under test)")
    print(f"[D1] output: {out}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[D1] stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
