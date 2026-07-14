#!/usr/bin/env python3
"""Headed Chromium smoke for Phase C / 1.4.0-dev (Patchright path).

Runs FoxDesk chromium_worker with chromium_backend=patchright (or auto),
collects ready + fingerprint_report, then stop.

Does not start the full desktop GUI. No payment or third-party abuse.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Phase C headed chromium_worker smoke")
    p.add_argument(
        "--backend",
        choices=("auto", "playwright", "patchright"),
        default="patchright",
        help="chromium_backend written into runtime JSON",
    )
    p.add_argument(
        "--require-webdriver-false",
        action="store_true",
        default=True,
        help="Fail if fingerprint webdriver is not false (default on)",
    )
    p.add_argument(
        "--allow-webdriver-true",
        action="store_true",
        help="Do not fail on webdriver=true (debug only)",
    )
    p.add_argument(
        "--json-out",
        default=str(ROOT / "docs" / "research" / "_smoke_phase_c_worker.json"),
    )
    p.add_argument(
        "--summary-out",
        default=str(ROOT / "docs" / "research" / "_smoke_phase_c_summary.json"),
    )
    p.add_argument("--timeout", type=float, default=90.0)
    return p.parse_args()


def run_chromium_worker(backend: str, user_data: Path, timeout: float) -> dict:
    runtime_id = str(uuid.uuid4())
    runtime_path = Path(tempfile.gettempdir()) / f"foxdesk-smoke-c-{runtime_id}.json"
    profile = {
        "name": "smoke-phase-c-chromium",
        "engine": "chromium",
        "chromium_backend": backend,
        "mode": "browser",
        "headless": False,
        "persistent_context": True,
        "user_data_dir": str(user_data),
        "startup_url": "about:blank",
        "locale": "en-US",
        "timezone": "America/New_York",
        "screen_width": 1280,
        "screen_height": 720,
        "block_webrtc": True,
        "webrtc_mode": "disable",
        "chromium_channel": "",
        "font_pack": "windows",
        "media_devices": "random",
        "_runtime_id": runtime_id,
        "_auto_fingerprint_probe": True,
    }
    runtime_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    cmd_path = runtime_path.with_suffix(".cmd.jsonl")
    result_path = runtime_path.with_suffix(".result.jsonl")
    cmd_path.write_text("", encoding="utf-8")
    result_path.write_text("", encoding="utf-8")

    worker = ROOT / "backend" / "chromium_worker.py"
    print("[smoke-c] chromium_worker:", worker, runtime_path, "backend=", backend, flush=True)
    proc = subprocess.Popen(
        [sys.executable, str(worker), str(runtime_path)],
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    logs: list[str] = []
    ready = False
    backend_emitted = None
    fingerprint = None
    deadline = time.time() + timeout
    try:
        while time.time() < deadline:
            line = proc.stdout.readline() if proc.stdout else ""
            if line:
                logs.append(line.rstrip())
                try:
                    evt = json.loads(line)
                except Exception:
                    evt = None
                if isinstance(evt, dict):
                    if evt.get("event") == "launching":
                        backend_emitted = evt.get("backend") or backend_emitted
                    if evt.get("event") == "ready":
                        ready = True
                        backend_emitted = evt.get("backend") or backend_emitted
                    if evt.get("event") == "fingerprint_report":
                        fingerprint = evt.get("report")
                    if evt.get("event") == "error":
                        break
            if ready and fingerprint is not None:
                break
            if proc.poll() is not None:
                break
            if not line:
                time.sleep(0.05)
        with open(cmd_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"id": "smoke-c-stop", "cmd": "stop"}) + "\n")
        try:
            proc.wait(timeout=20)
        except subprocess.TimeoutExpired:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
    finally:
        if proc.poll() is None:
            proc.kill()

    try:
        if proc.stdout:
            rest = proc.stdout.read() or ""
            for line in rest.splitlines():
                logs.append(line.rstrip())
    except Exception:
        pass

    payload: dict = {
        "ready": ready,
        "returncode": proc.returncode,
        "backend_requested": backend,
        "backend_emitted": backend_emitted,
        "fingerprint": fingerprint,
        "logs_tail": logs[-100:],
        "runtime_path": str(runtime_path),
    }
    if isinstance(fingerprint, dict):
        payload["webdriver"] = fingerprint.get("webdriver")
        payload["userAgent"] = fingerprint.get("userAgent") or fingerprint.get("ua")
    return payload


def main() -> int:
    args = parse_args()
    require_wd_false = bool(args.require_webdriver_false) and not bool(args.allow_webdriver_true)
    out_path = Path(args.json_out)
    summary_path = Path(args.summary_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    user_data = Path(tempfile.mkdtemp(prefix="foxdesk-smoke-c-"))
    summary: dict = {
        "app_version_hint": "1.4.0-dev",
        "phase": "C",
        "headed": True,
        "platform": sys.platform,
        "backend_requested": args.backend,
        "require_webdriver_false": require_wd_false,
        "worker": None,
        "ok": False,
        "notes": (
            "Phase C headed worker smoke. Proves launch + optional webdriver=false under Patchright. "
            "Not a commercial anti-detect or payment guarantee."
        ),
    }
    try:
        worker = run_chromium_worker(args.backend, user_data, args.timeout)
        out_path.write_text(json.dumps(worker, ensure_ascii=False, indent=2), encoding="utf-8")
        summary["worker"] = {
            "ready": worker.get("ready"),
            "returncode": worker.get("returncode"),
            "backend_emitted": worker.get("backend_emitted"),
            "webdriver": worker.get("webdriver"),
            "userAgent": (worker.get("userAgent") or "")[:120],
            "json_out": str(out_path),
        }
        ready_ok = bool(worker.get("ready"))
        wd = worker.get("webdriver")
        wd_ok = True
        if require_wd_false:
            wd_ok = wd is False
        summary["ok"] = ready_ok and wd_ok
        if not ready_ok:
            summary["fail_reason"] = "worker_not_ready"
        elif require_wd_false and wd is not False:
            summary["fail_reason"] = f"webdriver_expected_false_got_{wd!r}"
        backend_emitted = worker.get("backend_emitted")
        if args.backend == "patchright" and backend_emitted and backend_emitted != "patchright":
            summary["ok"] = False
            summary["fail_reason"] = f"backend_emitted={backend_emitted!r}"
    except Exception as exc:
        summary["ok"] = False
        summary["error"] = f"{type(exc).__name__}: {exc}"

    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
