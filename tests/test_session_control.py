from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from backend.session_control import send_worker_command


def test_send_worker_command_roundtrip(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime.json"
    runtime.write_text("{}", encoding="utf-8")
    cmd = runtime.with_suffix(".cmd.jsonl")
    res = runtime.with_suffix(".result.jsonl")
    cmd.write_text("", encoding="utf-8")
    res.write_text("", encoding="utf-8")

    def worker() -> None:
        # Wait for a command line then echo a result with matching id.
        deadline = time.time() + 5
        while time.time() < deadline:
            text = cmd.read_text(encoding="utf-8").strip()
            if text:
                row = json.loads(text.splitlines()[-1])
                payload = {"id": row["id"], "cmd": row.get("cmd"), "ok": True, "echo": row}
                with open(res, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(payload) + "\n")
                return
            time.sleep(0.05)

    threading.Thread(target=worker, daemon=True).start()
    result = send_worker_command(runtime, "ping", timeout=3.0)
    assert result["ok"] is True
    assert result["cmd"] == "ping"


def test_send_worker_command_timeout(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime.json"
    runtime.write_text("{}", encoding="utf-8")
    runtime.with_suffix(".cmd.jsonl").write_text("", encoding="utf-8")
    runtime.with_suffix(".result.jsonl").write_text("", encoding="utf-8")
    result = send_worker_command(runtime, "ping", timeout=0.4)
    assert result["ok"] is False
    assert "timeout" in str(result.get("error") or "").lower()
