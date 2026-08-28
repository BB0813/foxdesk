"""FoxDesk FastAPI application (composition root).

Since 1.4.1 the former monolith is split:
- backend/models.py       Pydantic models
- backend/core.py         paths, stores, process registry, activity log
- backend/local_auth.py   per-process API token + loopback middleware
- backend/engine_meta.py  pure engine naming / error humanization
- backend/engine_tools.py availability probes, worker commands, lifecycle
- backend/profile_logic.py launch validation, risk scoring, proxy assignment
- backend/proxy_test.py   proxy connectivity testing
- backend/cookie_io.py    cookie import/export helpers
- backend/backup_util.py  backup collection / restore sanitization
- backend/wiring.py       update / setup / proxy-health singletons
- backend/routes/*        one APIRouter per domain

`backend.app` still re-exports the previously public names so existing
tests, tooling, and the frozen entry point keep working unchanged.
"""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware  # noqa: F401 (kept for parity)

from backend import wiring
from backend.core import (  # noqa: F401  (re-exports)
    APP_DATA_DIR,
    APP_EXECUTABLE,
    APP_VERSION,
    CREATE_NO_WINDOW,
    DATA_DIR,
    GITHUB_REPO,
    PROFILE_SCHEMA_VERSION,
    PROFILES_DIR,
    RUNTIME_DIR,
    STATIC_DIR,
    WORKER,
    WORKER_CHROMIUM,
    ROOT,
    ActivityLog,
    ChannelStore,
    ManagedProcess,
    ProfileStore,
    ProcessRegistry,
    ProxyConfig,
    Profile,
    ProfileIn,
)
from backend.models import (  # noqa: F401  (re-exports)
    TaskRequest,
    LaunchRequest,
    ImportProfilesRequest,
    ProxyTestRequest,
    ChannelUpdateRequest,
    BatchLaunchRequest,
    BatchStopRequest,
    SetupStartRequest,
    SettingsUpdateRequest,
    UpdateCheckRequest,
    UpdateInstallRequest,
    ProxyPoolIn,
    ProxyPoolImportRequest,
    ProxyAssignRequest,
    BulkProxyRequest,
    ApplySuggestionRequest,
    NavigateRequest,
    EvaluateRequest,
    ScreenshotRequest,
    BackupRequest,
    BackupRestoreRequest,
)
from backend.core import (  # noqa: F401  (singleton re-exports)
    activity,
    channel_store,
    get_app_data_dir,
    migrate_legacy_data,
    now_iso,
    proxy_pool,
    registry,
    settings_store,
    store,
)
from backend.local_auth import (  # noqa: F401  (re-exports)
    API_TOKEN,
    API_TOKEN_HEADER,
    LocalApiTokenMiddleware,
    _is_loopback_host,
)
from backend.engine_meta import (  # noqa: F401  (re-exports)
    chromium_install_hint,
    humanize_chromium_launch_error,
    normalize_chromium_backend_name,
    normalize_engine_name,
)
from backend.engine_tools import (  # noqa: F401  (re-exports)
    camoufox_command,
    camoufox_path_info,
    camoufox_version_info,
    chromium_backend_available,
    cleanup_runtime_files,
    import_available,
    resolve_chromium_backend,
    run_short,
    start_process,
    worker_command,
    _wrap_runtime_proxy_secret,
)
from backend.profile_logic import (  # noqa: F401  (re-exports)
    apply_proxy_pool_to_profile,
    detect_google_chrome_install,
    environment_risks_for_profile,
    normalize_profile_paths,
    pick_proxy_from_pool,
    resolve_user_data_dir,
    validate_profile_for_launch,
)
from backend.proxy_test import (  # noqa: F401  (re-exports)
    _socks4_connect,
    _socks5_connect,
    _test_proxy_connection,
    _tls_wrap,
    test_proxy_item_for_health as _test_proxy_item_for_health,
)
from backend.cookie_io import (  # noqa: F401  (re-exports)
    find_cookies_sqlite as _find_cookies_sqlite,
    parse_netscape_cookies as _parse_netscape_cookies,
)
from backend.backup_util import (  # noqa: F401  (re-exports)
    _BACKUP_SAFE_ROOT_NAMES,
    collect_backup_files as _collect_backup_files,
    safe_restore_target as _safe_restore_target,
)
from backend.routes.system import (
    _validate_mirror_prefix,
    _validate_task_args,
    system,
)  # noqa: F401
from backend.routes.pages import router as pages_router
from backend.routes.system import router as system_router
from backend.routes.profiles import router as profiles_router
from backend.routes.sessions import router as sessions_router
from backend.routes.proxies import router as proxies_router
from backend.routes.backups import router as backups_router

app = FastAPI(
    title="FoxDesk",
    version=APP_VERSION,
    # Local tool: API surface must not be discoverable via /docs et al.
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.add_middleware(LocalApiTokenMiddleware)


def _shutdown_cleanup() -> None:
    """Stop every worker/browser on server shutdown so nothing is orphaned."""
    from backend.local_auth import _remove_token_file

    _remove_token_file()
    try:
        with registry.lock:
            item_ids = list(registry.items.keys())
        for item_id in item_ids:
            try:
                registry.stop(item_id)
            except Exception:
                pass
    except Exception:
        pass


app.router.add_event_handler("shutdown", _shutdown_cleanup)
app.router.add_event_handler("startup", wiring.proxy_health.start)
app.mount("/assets", StaticFiles(directory=STATIC_DIR), name="assets")

# Registration order mirrors the historical app.py ordering per domain and
# avoids any path-parameter shadowing between them.
app.include_router(pages_router)
app.include_router(system_router)
app.include_router(profiles_router)
app.include_router(sessions_router)
app.include_router(proxies_router)
app.include_router(backups_router)

# --- Backwards-compatible singleton aliases (tests / tooling) ---
update_manager = wiring.update_manager  # noqa: F401
setup_manager = wiring.setup_manager  # noqa: F401
proxy_health = wiring.proxy_health  # noqa: F401
