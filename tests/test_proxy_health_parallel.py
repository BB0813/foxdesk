"""Proxy health scheduler: parallel probing + batch result flush."""

from __future__ import annotations

import threading
import time

from backend.proxy_health import ProxyHealthScheduler


def _make_scheduler(items, mark_results, mark_result=None, test_proxy=None):
    if mark_result is None:
        mark_result = lambda proxy_id, result: None  # noqa: E731
    if test_proxy is None:
        test_proxy = lambda item: {"ok": True, "latency_ms": 1}  # noqa: E731
    return ProxyHealthScheduler(
        list_proxies=lambda: items,
        test_proxy=test_proxy,
        mark_result=mark_result,
        mark_results=mark_results,
    )


class TestParallelRunOnce:
    def test_parallel_pass_batches_results(self):
        items = [{"id": f"p{i}", "server": f"http://p{i}:1"} for i in range(5)]
        flushed = {}

        def flush(results):
            flushed.update(results)
            return len(results)

        sched = _make_scheduler(items, flush)
        summary = sched.run_once()
        assert summary["ok"] is True
        assert summary["checked"] == 5
        assert summary["passed"] == 5
        # One batch flush covering every probe
        assert set(flushed.keys()) == {item["id"] for item in items}

    def test_parallel_speedup(self):
        """5 probes x 0.3s each should complete well under sequential 1.5s."""
        items = [{"id": f"p{i}", "server": f"http://p{i}:1"} for i in range(5)]

        def slow_probe(item):
            time.sleep(0.3)
            return {"ok": True, "latency_ms": 300}

        sched = _make_scheduler(items, lambda results: len(results), test_proxy=slow_probe)
        start = time.monotonic()
        summary = sched.run_once()
        elapsed = time.monotonic() - start
        assert summary["passed"] == 5
        assert elapsed < 1.0  # sequential would be ~1.5s

    def test_probe_exception_becomes_failure(self):
        items = [{"id": "a", "server": "http://a:1"}, {"id": "b", "server": "http://b:1"}]

        def boom(item):
            if item["id"] == "b":
                raise RuntimeError("socket exploded")
            return {"ok": True, "latency_ms": 1}

        sched = _make_scheduler(items, lambda results: len(results), test_proxy=boom)
        summary = sched.run_once()
        assert summary["passed"] == 1
        assert summary["failed"] == 1
        assert summary["details"][1]["error"] == "socket exploded"

    def test_single_item_uses_per_item_path(self):
        items = [{"id": "only", "server": "http://x:1"}]
        per_item_calls = []

        def mark(proxy_id, result):
            per_item_calls.append(proxy_id)

        sched = _make_scheduler(items, mark_results=lambda r: None, mark_result=mark)
        summary = sched.run_once()
        assert summary["passed"] == 1
        assert per_item_calls == ["only"]

    def test_batch_flush_failure_falls_back_to_per_item(self):
        items = [{"id": "x", "server": "http://x:1"}, {"id": "y", "server": "http://y:1"}]
        per_item_calls = []
        lock = threading.Lock()

        def mark(proxy_id, result):
            with lock:
                per_item_calls.append(proxy_id)

        def broken_flush(results):
            raise RuntimeError("flush failed")

        sched = _make_scheduler(items, mark_results=broken_flush, mark_result=mark)
        summary = sched.run_once()
        assert summary["passed"] == 2
        assert sorted(per_item_calls) == ["x", "y"]
