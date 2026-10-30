from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

# Per-result-file read offsets (incremental scans for long sessions)
_read_offsets: dict[str, int] = {}
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

    # Long-lived automation sessions grow the result file unboundedly; reading
    # the whole file on every poll is O(n^2). Track per-file read offsets.
    key = str(res_file)
    start_offset = _read_offsets.get(key)
    if start_offset is None:
        start_offset = res_file.stat().st_size if res_file.exists() else 0
    with open(cmd_file, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(body, ensure_ascii=False) + "\n")

    deadline = time.time() + max(1.0, timeout)
    consumed = 0
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
        consumed = len(data) - start_offset
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
                _read_offsets[key] = start_offset + len(data)
                return row
        time.sleep(0.15)

    # Advance past consumed bytes even on timeout so the next command does
    # not re-scan the same lines forever.
    if consumed:
        _read_offsets[key] = start_offset + consumed
    return {
        "id": req_id,
        "cmd": cmd,
        "ok": False,
        "error": f"timeout waiting for worker command result ({timeout}s)",
    }
