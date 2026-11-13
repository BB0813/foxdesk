"""Subscription store + scheduler tests (no network)."""
from __future__ import annotations

import threading
import time

import pytest

from backend.subscriptions import (
    SubscriptionScheduler,
    SubscriptionStore,
    _sub_tag,
)


@pytest.fixture()
def store(tmp_path):
    return SubscriptionStore(tmp_path / "subscriptions.json")


def test_store_crud_roundtrip(store):
    entry = store.add("https://example.com/sub", "test", 360)
    assert entry["enabled"] is True
    assert entry["interval_minutes"] == 360
    assert store.get(entry["id"])["url"] == "https://example.com/sub"

    updated = store.update(entry["id"], {"enabled": False, "interval_minutes": 0, "name": "renamed"})
    assert updated["enabled"] is False
    assert updated["interval_minutes"] == 0
    assert updated["name"] == "renamed"

    store.mark_result(entry["id"], 7, None)
    got = store.get(entry["id"])
    assert got["last_count"] == 7
    assert got["last_status"] == "ok"
    assert got["last_refresh_ts"] is not None

    assert store.remove(entry["id"]) is True
    assert store.list() == []
    assert store.remove(entry["id"]) is False


def test_store_mark_error(store):
    entry = store.add("https://example.com/sub", "", 360)
    store.mark_result(entry["id"], 0, "boom")
    got = store.get(entry["id"])
    assert got["last_status"] == "error"
    assert got["last_error"] == "boom"
    assert got["last_count"] == 0


def test_scheduler_sweeps_due_entries(store):
    calls: list[str] = []

    def fake_refresh(s, sub_id):
        calls.append(sub_id)
        return {"ok": True, "imported": 3}

    # entry never refreshed + interval 60m -> due immediately
    store.add("https://example.com/a", "a", 60)
    # entry disabled -> skipped
    dis = store.add("https://example.com/b", "b", 60)
    store.update(dis["id"], {"enabled": False})
    # entry manual-only (interval 0) -> skipped
    store.add("https://example.com/c", "c", 0)

    scheduler = SubscriptionScheduler(store, poll_seconds=1, refresher=fake_refresh)
    scheduler.run_once()
    assert len(calls) == 1

    # a recently refreshed entry is not due again
    store.mark_result(calls[0], 3, None)
    scheduler.run_once()
    assert len(calls) == 1


def test_scheduler_thread_starts_and_stops(store):
    started = threading.Event()

    def fake_refresh(s, sub_id):
        started.set()
        return {"ok": True, "imported": 0}

    # interval at the 30-minute minimum; backdate last refresh far past it
    store.add("https://example.com/x", "x", 30)
    entries = store.list()
    for e in entries:
        e["last_refresh_ts"] = time.time() - 10_000  # >> 30*60s
    store._write(entries)

    scheduler = SubscriptionScheduler(store, poll_seconds=0.05, refresher=fake_refresh)
    scheduler.start()
    assert started.wait(timeout=5), "scheduler should sweep due entries"
    scheduler.stop()
    scheduler._thread.join(timeout=2)
    assert not scheduler._thread.is_alive()


def test_sub_tag_format():
    assert _sub_tag("abc-123") == "sub:abc-123"
