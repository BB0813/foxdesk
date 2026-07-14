from __future__ import annotations

import threading
import time
from typing import Any, Callable


class ProxyHealthScheduler:
    """Background proxy health checker."""

    def __init__(
        self,
        *,
        list_proxies: Callable[[], list[dict[str, Any]]],
        test_proxy: Callable[[dict[str, Any]], dict[str, Any]],
        mark_result: Callable[[str, dict[str, Any]], Any],
        interval_seconds: float = 300.0,
        enabled_provider: Callable[[], bool] | None = None,
    ) -> None:
        self.list_proxies = list_proxies
        self.test_proxy = test_proxy
        self.mark_result = mark_result
        self.interval_seconds = interval_seconds
        self.enabled_provider = enabled_provider or (lambda: True)
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._lock = threading.RLock()
        self._running_pass = False
        self.last_run_at: float | None = None
        self.last_summary: dict[str, Any] = {}

    def configure(self, *, interval_seconds: float | None = None) -> None:
        if interval_seconds is not None and interval_seconds >= 30:
            self.interval_seconds = float(interval_seconds)

    def start(self) -> None:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop.clear()
            self._thread = threading.Thread(target=self._loop, daemon=True, name="proxy-health")
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def status(self) -> dict[str, Any]:
        return {
            "enabled": bool(self.enabled_provider()),
            "interval_seconds": self.interval_seconds,
            "running_pass": self._running_pass,
            "last_run_at": self.last_run_at,
            "last_summary": self.last_summary,
        }

    def run_once(self) -> dict[str, Any]:
        with self._lock:
            if self._running_pass:
                return {"ok": False, "error": "health check already running", **self.status()}
            self._running_pass = True
        try:
            items = self.list_proxies() or []
            ok = 0
            fail = 0
            details: list[dict[str, Any]] = []
            for item in items:
                proxy_id = item.get("id")
                if not proxy_id:
                    continue
                try:
                    result = self.test_proxy(item)
                    self.mark_result(str(proxy_id), result)
                    if result.get("ok"):
                        ok += 1
                    else:
                        fail += 1
                    details.append(
                        {
                            "id": proxy_id,
                            "ok": bool(result.get("ok")),
                            "latency_ms": result.get("latency_ms"),
                            "error": result.get("error"),
                        }
                    )
                except Exception as exc:
                    fail += 1
                    err = {"ok": False, "error": str(exc)}
                    try:
                        self.mark_result(str(proxy_id), err)
                    except Exception:
                        pass
                    details.append({"id": proxy_id, "ok": False, "error": str(exc)})
            summary = {
                "ok": True,
                "checked": ok + fail,
                "passed": ok,
                "failed": fail,
                "details": details[:100],
            }
            self.last_run_at = time.time()
            self.last_summary = summary
            return summary
        finally:
            with self._lock:
                self._running_pass = False

    def _loop(self) -> None:
        # First run delayed so app can finish boot.
        self._stop.wait(15)
        while not self._stop.is_set():
            if self.enabled_provider():
                try:
                    self.run_once()
                except Exception:
                    pass
            self._stop.wait(max(30.0, float(self.interval_seconds)))
