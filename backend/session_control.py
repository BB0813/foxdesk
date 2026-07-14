from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any


def command_path(runtime_path: str | Path) -> Path:
    return Path(runtime_path).with_suffix(".cmd.jsonl")


def result_path(runtime_path: str | Path) -> Path:
    return Path(runtime_path).with_suffix(".result.jsonl")


def send_worker_command(
    runtime_path: str | Path,
    cmd: str,
    *,
    payload: dict[str, Any] | None = None,
    timeout: float = 45.0,
) -> dict[str, Any]:
    """Append a JSON command for the worker and wait for a matching result line."""
    runtime_path = Path(runtime_path)
    if not runtime_path.exists():
        raise FileNotFoundError(f"runtime profile missing: {runtime_path}")

    req_id = str(uuid.uuid4())
    body = {"id": req_id, "cmd": cmd, **(payload or {})}
    cmd_file = command_path(runtime_path)
    res_file = result_path(runtime_path)

    # Record current result file size so we only read new lines.
    start_offset = res_file.stat().st_size if res_file.exists() else 0
    with open(cmd_file, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(body, ensure_ascii=False) + "\n")

    deadline = time.time() + max(1.0, timeout)
    while time.time() < deadline:
        if not res_file.exists():
            time.sleep(0.15)
            continue
        try:
            data = res_file.read_bytes()
        except OSError:
            time.sleep(0.15)
            continue
        if len(data) <= start_offset:
            time.sleep(0.15)
            continue
        chunk = data[start_offset:].decode("utf-8", errors="replace")
        for line in chunk.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            if isinstance(row, dict) and row.get("id") == req_id:
                return row
        time.sleep(0.15)

    return {
        "id": req_id,
        "cmd": cmd,
        "ok": False,
        "error": f"timeout waiting for worker command result ({timeout}s)",
    }
