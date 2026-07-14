#!/usr/bin/env python3
"""Headed dual-engine smoke for Phase A / 1.4.0-dev.

Runs:
  1) Playwright Chromium headed probe (via tools/poc_chromium_launch.py path)
  2) FoxDesk chromium_worker with a temp runtime JSON (navigate + fingerprint + stop)

Does not start the full desktop GUI. Safe local research only.
No payment or third-party abuse.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def run_poc_headed(json_out: Path) -> dict:
    cmd = [
        sys.executable,
        str(ROOT / "tools" / "poc_chromium_launch.py"),
        "--headed",
        "--probe",
        "--url",
        "about:blank",
        "--keep-open",
        "1.5",
        "--json-out",
        str(json_out),
    ]
    print("[smoke] poc headed:", " ".join(cmd), flush=True)
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=120)
    out = {
        "returncode": proc.returncode,
        "stdout_tail": (proc.stdout or "")[-2000:],
        "stderr_tail": (proc.stderr or "")[-2000:],
    }
    if json_out.exists():
        try:
            out["result"] = json.loads(json_out.read_text(encoding="utf-8"))
        except Exception as exc:
            out["result_error"] = str(exc)
    return out


def run_chromium_worker(json_out: Path, user_data: Path) -> dict:
    runtime_id = str(uuid.uuid4())
    runtime_path = Path(tempfile.gettempdir()) / f"foxdesk-smoke-{runtime_id}.json"
    profile = {
        "name": "smoke-chromium",
        "engine": "chromium",
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
        "_runtime_id": runtime_id,
        "_auto_fingerprint_probe": True,
    }
    runtime_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    cmd_path = runtime_path.with_suffix(".cmd.jsonl")
    result_path = runtime_path.with_suffix(".result.jsonl")
    cmd_path.write_text("", encoding="utf-8")
    result_path.write_text("", encoding="utf-8")

    worker = ROOT / "backend" / "chromium_worker.py"
    print("[smoke] chromium_worker:", worker, runtime_path, flush=True)
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
    fingerprint = None
    deadline = time.time() + 90
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
                    if evt.get("event") == "ready":
                        ready = True
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
        # Ask worker to stop cleanly.
        with open(cmd_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"id": "smoke-stop", "cmd": "stop"}) + "\n")
        try:
            proc.wait(timeout=20)
        except subprocess.TimeoutExpired:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
    finally:
        if proc.poll() is not None:
            pass
        elif proc.poll() is None:
            proc.kill()

    # Drain remaining logs
    try:
        if proc.stdout:
            rest = proc.stdout.read() or ""
            for line in rest.splitlines():
                logs.append(line.rstrip())
    except Exception:
        pass

    payload = {
        "ready": ready,
        "returncode": proc.returncode,
        "fingerprint": fingerprint,
        "logs_tail": logs[-80:],
        "runtime_path": str(runtime_path),
    }
    # Parse webdriver from fingerprint if present
    if isinstance(fingerprint, dict):
        payload["webdriver"] = fingerprint.get("webdriver")
        payload["userAgent"] = fingerprint.get("userAgent") or fingerprint.get("ua")
    json_out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def main() -> int:
    out_dir = ROOT / "docs" / "research"
    out_dir.mkdir(parents=True, exist_ok=True)
    poc_json = out_dir / "_smoke_headed_poc.json"
    worker_json = out_dir / "_smoke_headed_worker.json"
    summary_path = out_dir / "_smoke_headed_summary.json"

    user_data = Path(tempfile.mkdtemp(prefix="foxdesk-smoke-chromium-"))
    summary: dict = {
        "app_version_hint": "1.4.0-dev",
        "headed": True,
        "platform": sys.platform,
        "poc": None,
        "worker": None,
        "ok": False,
    }
    try:
        summary["poc"] = run_poc_headed(poc_json)
        summary["worker"] = run_chromium_worker(worker_json, user_data)
        poc_ok = bool((summary["poc"].get("result") or {}).get("ok"))
        worker_ok = bool(summary["worker"].get("ready"))
        summary["ok"] = poc_ok and worker_ok
        summary["notes"] = (
            "Headed smoke only proves L1 launch path. "
            "webdriver/automation signals remaining are expected until Phase C."
        )
    except Exception as exc:
        summary["ok"] = False
        summary["error"] = f"{type(exc).__name__}: {exc}"

    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
