"""Cookie import/export helpers (SQLite read, Netscape parsing)."""
from __future__ import annotations

from pathlib import Path
from typing import Any


def find_cookies_sqlite(user_data_dir: Path) -> Path | None:
    candidates = [
        user_data_dir / "cookies.sqlite",
        user_data_dir / "cookies.sqlite.corrupted",
    ]
    # Firefox-style nested profiles
    for path in user_data_dir.rglob("cookies.sqlite"):
        candidates.append(path)
    for path in candidates:
        if path.exists() and path.is_file():
            return path
    return None


def parse_netscape_cookies(text: str) -> list[dict[str, Any]]:
    cookies: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or (line.startswith("#") and not line.startswith("#HttpOnly_")):
            continue
        parts = line.split("\t")
        if len(parts) < 7:
            continue
        domain, _flag, path, secure, expires, name, value = parts[:7]
        cookie: dict[str, Any] = {
            "domain": domain,
            "host": domain,
            "path": path or "/",
            "secure": str(secure).upper() == "TRUE",
            "expires": int(float(expires)) if expires not in ("", "0") else None,
            "name": name,
            "value": value,
            "httpOnly": domain.startswith("#HttpOnly_") or domain.startswith("."),
        }
        if cookie["domain"].startswith("#HttpOnly_"):
            cookie["domain"] = cookie["domain"].replace("#HttpOnly_", "", 1)
            cookie["host"] = cookie["domain"]
            cookie["httpOnly"] = True
        cookies.append(cookie)
    return cookies
