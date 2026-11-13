"""Proxy subscription store + auto-refresh scheduler.

A subscription is an HTTPS URL returning proxy node lines (vless://…,
base64-wrapped, or plain). Each subscription's nodes are tagged
``sub:<id>`` in the proxy pool; a refresh replaces exactly those nodes,
leaving manually imported entries untouched.
"""
from __future__ import annotations

import base64
import json
import logging
import threading
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Callable

from backend.core import now_iso, proxy_pool
from backend.storage_util import atomic_write_json

log = logging.getLogger(__name__)

SUB_TAG_PREFIX = "sub:"
MIN_INTERVAL_MINUTES = 30
FETCH_TIMEOUT = 20
MAX_BYTES = 2 * 1024 * 1024


class SubscriptionError(RuntimeError):
    pass


def _sub_tag(sub_id: str) -> str:
    return SUB_TAG_PREFIX + str(sub_id)


# ────────────────────────── store ──────────────────────────


class SubscriptionStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.lock = threading.RLock()
        if not self.path.exists():
            atomic_write_json(self.path, [])

    def _read(self) -> list[dict[str, Any]]:
        with self.lock:
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                return []
            if not isinstance(raw, list):
                return []
            return [e for e in raw if isinstance(e, dict)]

    def _write(self, entries: list[dict[str, Any]]) -> None:
        with self.lock:
            atomic_write_json(self.path, entries)

    def list(self) -> list[dict[str, Any]]:
        return self._read()

    def get(self, sub_id: str) -> dict[str, Any] | None:
        return next((e for e in self._read() if e.get("id") == sub_id), None)

    def add(
        self,
        url: str,
        name: str = "",
        interval_minutes: int = 360,
    ) -> dict[str, Any]:
        entry = {
            "id": str(uuid.uuid4()),
            "url": url,
            "name": (name or "").strip() or url,
            "enabled": True,
            "interval_minutes": max(0, int(interval_minutes)),
            "last_refresh_at": None,
            "last_refresh_ts": None,
            "last_status": None,
            "last_count": 0,
            "last_error": None,
            "created_at": now_iso(),
        }
        with self.lock:
            entries = self._read()
            entries.append(entry)
            self._write(entries)
        return entry

    def update(self, sub_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
        with self.lock:
            entries = self._read()
            for entry in entries:
                if entry.get("id") != sub_id:
                    continue
                if "name" in data:
                    entry["name"] = str(data["name"] or entry["url"]).strip() or entry["url"]
                if "enabled" in data:
                    entry["enabled"] = bool(data["enabled"])
                if "interval_minutes" in data:
                    entry["interval_minutes"] = max(0, int(data["interval_minutes"]))
                self._write(entries)
                return entry
        return None

    def remove(self, sub_id: str) -> bool:
        with self.lock:
            entries = self._read()
            kept = [e for e in entries if e.get("id") != sub_id]
            if len(kept) == len(entries):
                return False
            self._write(kept)
            return True

    def mark_result(self, sub_id: str, count: int, error: str | None = None) -> None:
        with self.lock:
            entries = self._read()
            for entry in entries:
                if entry.get("id") != sub_id:
                    continue
                entry["last_refresh_at"] = now_iso()
                entry["last_refresh_ts"] = time.time()
                entry["last_count"] = int(count)
                entry["last_status"] = "error" if error else "ok"
                entry["last_error"] = error
                break
            self._write(entries)


# ────────────────────── fetch + import ──────────────────────


def validate_public_https(url: str) -> str:
    """SSRF guard: https only, and every resolved address must be public."""
    import ipaddress
    import socket
    from urllib.parse import urlparse

    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise SubscriptionError("subscription URL must be https://")
    try:
        infos = socket.getaddrinfo(parsed.hostname, parsed.port or 443)
    except Exception as exc:
        raise SubscriptionError(f"cannot resolve host: {exc}") from None
    for info in infos:
        addr = info[4][0]
        ip = ipaddress.ip_address(addr)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise SubscriptionError("subscription host resolves to a non-public address")
    return url


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch_subscription_text(url: str) -> str:
    """Fetch a subscription body: every redirect hop revalidated, cap 2 MB."""
    validate_public_https(url)
    opener = urllib.request.build_opener(_NoRedirect)
    current = url
    for _hop in range(4):
        req = urllib.request.Request(current, headers={"User-Agent": "FoxDesk/subscription"})
        try:
            with opener.open(req, timeout=FETCH_TIMEOUT) as resp:
                raw = resp.read(MAX_BYTES + 1)
        except urllib.error.HTTPError as exc:
            if exc.code in (301, 302, 303, 307, 308) and exc.headers.get("Location"):
                from urllib.parse import urljoin

                current = urljoin(current, exc.headers["Location"])
                validate_public_https(current)
                continue
            raise SubscriptionError(f"subscription fetch failed: {exc}") from None
        if len(raw) > MAX_BYTES:
            raise SubscriptionError("subscription too large (>2 MB)")
        text = raw.decode("utf-8", errors="replace")
        break
    else:
        raise SubscriptionError("too many redirects")
    if not text.strip():
        raise SubscriptionError("empty subscription")
    stripped = "".join(text.split())
    if not stripped.lower().startswith(("vless://", "vmess://", "trojan://", "ss://", "http")):
        try:
            pad = "=" * (-len(stripped) % 4)
            decoded = base64.b64decode(stripped + pad, validate=False).decode("utf-8", errors="replace")
            if "://" in decoded:
                text = decoded
        except Exception:
            pass
    return text


def subscription_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def remove_subscription_nodes(sub_id: str) -> int:
    tag = _sub_tag(sub_id)
    removed = 0
    for item in proxy_pool.all():
        if tag in (item.get("tags") or []):
            try:
                proxy_pool.delete(item["id"])
                removed += 1
            except Exception:
                pass
    return removed


def import_for_subscription(sub_id: str, url: str) -> int:
    """Fetch + import + tag nodes for one subscription. Returns node count."""
    text = fetch_subscription_text(url)
    imported = proxy_pool.import_lines(subscription_lines(text))
    tag = _sub_tag(sub_id)
    for item in imported:
        tags = list(item.get("tags") or [])
        if tag not in tags:
            tags.append(tag)
            proxy_pool.update(item["id"], {"tags": tags})
    return len(imported)


def refresh_subscription(store: SubscriptionStore, sub_id: str) -> dict[str, Any]:
    entry = store.get(sub_id)
    if entry is None:
        raise SubscriptionError("subscription not found")
    try:
        remove_subscription_nodes(sub_id)
        count = import_for_subscription(sub_id, str(entry.get("url") or ""))
        store.mark_result(sub_id, count, None)
        return {"ok": True, "imported": count}
    except SubscriptionError as exc:
        store.mark_result(sub_id, 0, str(exc))
        return {"ok": False, "error": str(exc)}
    except Exception as exc:
        store.mark_result(sub_id, 0, str(exc))
        return {"ok": False, "error": str(exc)}


# ────────────────────────── scheduler ──────────────────────────


class SubscriptionScheduler:
    """Daemon loop refreshing enabled subscriptions whose interval elapsed."""

    def __init__(
        self,
        store: SubscriptionStore,
        poll_seconds: float = 60.0,
        refresher: Callable[[SubscriptionStore, str], dict[str, Any]] | None = None,
    ) -> None:
        self.store = store
        self.poll_seconds = poll_seconds
        self._refresher = refresher or refresh_subscription
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._lock = threading.RLock()
        self.last_run_at: float | None = None
        self.last_result: dict[str, Any] = {}

    def start(self) -> None:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop.clear()
            self._thread = threading.Thread(target=self._loop, daemon=True, name="subscription-refresh")
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def status(self) -> dict[str, Any]:
        return {
            "last_run_at": self.last_run_at,
            "last_result": self.last_result,
            "poll_seconds": self.poll_seconds,
        }

    def run_once(self) -> dict[str, Any]:
        with self._lock:
            self.last_run_at = time.time()
        refreshed: list[dict[str, Any]] = []
        now = time.time()
        for entry in self.store.list():
            if not entry.get("enabled"):
                continue
            interval = int(entry.get("interval_minutes") or 0) * 60
            if interval < MIN_INTERVAL_MINUTES * 60:
                continue
            last = entry.get("last_refresh_ts")
            if last is not None and now - float(last) < interval:
                continue
            result = self._refresher(self.store, str(entry["id"]))
            refreshed.append({"id": entry["id"], **result})
        with self._lock:
            self.last_result = {"refreshed": refreshed}
        return self.last_result

    def _loop(self) -> None:
        while not self._stop.wait(self.poll_seconds):
            try:
                self.run_once()
            except Exception as exc:
                log.warning("subscription sweep failed: %s", exc)
