from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from backend.storage_util import (
    atomic_write_json,
    is_protected_secret,
    protect_secret,
    unprotect_secret,
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_proxy_server(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    if "://" not in value:
        value = f"http://{value}"
    allowed = ("http://", "https://", "socks4://", "socks5://")
    if not value.lower().startswith(allowed):
        raise ValueError("proxy server must use http://, https://, socks4://, or socks5://")
    return value


def parse_proxy_line(line: str) -> dict[str, str]:
    """
    Accept:
      scheme://user:pass@host:port
      scheme://host:port
      host:port
      host:port:user:pass
    """
    raw = (line or "").strip()
    if not raw or raw.startswith("#"):
        return {}
    username = ""
    password = ""
    server = raw
    if "://" not in raw and raw.count(":") >= 3:
        # host:port:user:pass
        host, port, username, password = raw.split(":", 3)
        server = f"http://{host}:{port}"
    else:
        if "://" not in server:
            server = f"http://{server}"
        parsed = urlparse(server)
        if parsed.username:
            username = parsed.username or ""
            password = parsed.password or ""
            # rebuild without credentials for server field
            host = parsed.hostname or ""
            port = f":{parsed.port}" if parsed.port else ""
            server = f"{parsed.scheme}://{host}{port}"
    server = normalize_proxy_server(server)
    return {"server": server, "username": username, "password": password}


class ProxyPoolStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.lock = threading.RLock()
        if not self.path.exists():
            atomic_write_json(self.path, [])
        else:
            # Upgrade plaintext passwords at rest on first load.
            try:
                self._migrate_secrets()
            except Exception:
                pass

    def _decode_item(self, item: dict[str, Any]) -> dict[str, Any]:
        out = dict(item)
        out["password"] = unprotect_secret(out.get("password") or "")
        return out

    def _encode_item(self, item: dict[str, Any]) -> dict[str, Any]:
        out = dict(item)
        pwd = out.get("password") or ""
        if pwd and not is_protected_secret(str(pwd)):
            out["password"] = protect_secret(str(pwd))
        return out

    def _read(self) -> list[dict[str, Any]]:
        with self.lock:
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                raw = []
            if not isinstance(raw, list):
                raw = []
            return [self._decode_item(item if isinstance(item, dict) else {}) for item in raw]

    def _write(self, items: list[dict[str, Any]]) -> None:
        with self.lock:
            encoded = [self._encode_item(item) for item in items]
            atomic_write_json(self.path, encoded)

    def _migrate_secrets(self) -> None:
        with self.lock:
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                return
            if not isinstance(raw, list):
                return
            changed = False
            encoded: list[dict[str, Any]] = []
            for item in raw:
                if not isinstance(item, dict):
                    continue
                row = dict(item)
                pwd = row.get("password") or ""
                if pwd and not is_protected_secret(str(pwd)):
                    row["password"] = protect_secret(str(pwd))
                    changed = True
                encoded.append(row)
            if changed:
                atomic_write_json(self.path, encoded)

    def all(self) -> list[dict[str, Any]]:
        return self._read()

    def get(self, proxy_id: str) -> dict[str, Any]:
        for item in self._read():
            if item.get("id") == proxy_id:
                return item
        raise KeyError(proxy_id)

    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        items = self._read()
        item = {
            "id": str(uuid.uuid4()),
            "name": (data.get("name") or "Proxy").strip() or "Proxy",
            "server": normalize_proxy_server(data.get("server") or ""),
            "username": data.get("username") or "",
            "password": data.get("password") or "",
            "tags": data.get("tags") or [],
            "notes": data.get("notes") or "",
            "last_ok": None,
            "last_latency_ms": None,
            "last_exit_ip": None,
            "last_error": None,
            "last_checked_at": None,
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
        if not item["server"]:
            raise ValueError("server is required")
        items.append(item)
        self._write(items)
        return item

    def update(self, proxy_id: str, data: dict[str, Any]) -> dict[str, Any]:
        items = self._read()
        for idx, item in enumerate(items):
            if item.get("id") != proxy_id:
                continue
            item = dict(item)
            if "name" in data and data["name"] is not None:
                item["name"] = str(data["name"]).strip() or item["name"]
            if "server" in data and data["server"] is not None:
                item["server"] = normalize_proxy_server(str(data["server"]))
            if "username" in data and data["username"] is not None:
                item["username"] = str(data["username"])
            if "password" in data and data["password"] is not None:
                item["password"] = str(data["password"])
            if "tags" in data and data["tags"] is not None:
                item["tags"] = list(data["tags"])
            if "notes" in data and data["notes"] is not None:
                item["notes"] = str(data["notes"])
            item["updated_at"] = now_iso()
            items[idx] = item
            self._write(items)
            return item
        raise KeyError(proxy_id)

    def delete(self, proxy_id: str) -> None:
        items = self._read()
        remaining = [item for item in items if item.get("id") != proxy_id]
        if len(remaining) == len(items):
            raise KeyError(proxy_id)
        self._write(remaining)

    def import_lines(self, lines: list[str], replace: bool = False) -> list[dict[str, Any]]:
        imported: list[dict[str, Any]] = []
        items = [] if replace else self._read()
        for line in lines:
            parsed = parse_proxy_line(line)
            if not parsed.get("server"):
                continue
            item = {
                "id": str(uuid.uuid4()),
                "name": parsed["server"],
                "server": parsed["server"],
                "username": parsed.get("username") or "",
                "password": parsed.get("password") or "",
                "tags": [],
                "notes": "",
                "last_ok": None,
                "last_latency_ms": None,
                "last_exit_ip": None,
                "last_error": None,
                "last_checked_at": None,
                "created_at": now_iso(),
                "updated_at": now_iso(),
            }
            items.append(item)
            imported.append(item)
        self._write(items)
        return imported

    def mark_test_result(self, proxy_id: str, result: dict[str, Any]) -> dict[str, Any]:
        items = self._read()
        for idx, item in enumerate(items):
            if item.get("id") != proxy_id:
                continue
            item = dict(item)
            item["last_ok"] = bool(result.get("ok"))
            item["last_latency_ms"] = result.get("latency_ms")
            item["last_exit_ip"] = result.get("exit_ip")
            item["last_error"] = result.get("error")
            item["last_checked_at"] = now_iso()
            item["updated_at"] = now_iso()
            items[idx] = item
            self._write(items)
            return item
        raise KeyError(proxy_id)
