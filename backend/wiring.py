"""Service wiring: update manager, guided setup, proxy health scheduler.

Instantiated at import time exactly like the original backend/app.py did,
but isolated here so route modules can depend on these singletons without
import cycles (core → stores; engine_tools → core; wiring → both).
"""
from __future__ import annotations

import sys
from pathlib import Path

from backend.core import (
    APP_EXECUTABLE,
    APP_VERSION,
    CREATE_NO_WINDOW,
    DATA_DIR,
    GITHUB_REPO,
    ROOT,
    channel_store,
    proxy_pool,
    registry,
    settings_store,
)
from backend.engine_tools import camoufox_command, import_available
from backend.proxy_test import test_proxy_item_for_health
from backend.proxy_health import ProxyHealthScheduler
from backend.setup_manager import SetupManager
from backend.update_manager import UpdateManager


def _channel_prefix(channel_id: str) -> str | None:
    for ch in channel_store.all():
        if ch.get("id") == channel_id:
            prefix = (ch.get("prefix") or "").strip()
            return prefix or None
    return None


update_manager = UpdateManager(
    app_version=APP_VERSION,
    github_repo=GITHUB_REPO,
    download_dir=DATA_DIR / "updates",
    user_agent=f"FoxDesk/{APP_VERSION}",
    # Never execute a downloaded installer without a verified checksum.
    require_checksum=True,
    token_provider=settings_store.get_github_token,
    mirror_provider=settings_store.get_update_mirror,
)
registry.idle_session_minutes_provider = lambda: settings_store.get().get("idle_session_minutes", 0)

proxy_health = ProxyHealthScheduler(
    list_proxies=proxy_pool.all,
    test_proxy=test_proxy_item_for_health,
    mark_result=proxy_pool.mark_test_result,
    # Batch flush: one read-modify-write per pass (parallel probes would
    # otherwise race per-item read/modify/write in the JSON store).
    mark_results=proxy_pool.mark_test_results,
    interval_seconds=float(settings_store.get().get("proxy_check_interval_sec") or 300),
    enabled_provider=lambda: bool(settings_store.get().get("proxy_auto_check", True)),
)
# Started on app startup (not import) so tests / tooling importing backend.app
# never fire real proxy probes. Registered in backend/app.py.

setup_manager = SetupManager(
    is_frozen=bool(getattr(sys, "frozen", False)),
    executable=APP_EXECUTABLE,
    root=ROOT if not getattr(sys, "frozen", False) else Path(sys.executable).resolve().parent,
    create_no_window=CREATE_NO_WINDOW,
    camoufox_command=camoufox_command,
    import_available=import_available,
    channel_prefix=_channel_prefix,
    marker_path=DATA_DIR / "setup.completed",
)
