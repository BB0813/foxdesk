"""Local API authentication: per-process token + loopback-only middleware."""
from __future__ import annotations

import atexit
import secrets
import tempfile
from pathlib import Path

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# Localhost API token: blocks casual cross-process abuse on 127.0.0.1.
# Token is generated per process and injected into the UI shell.
API_TOKEN = secrets.token_urlsafe(32)
API_TOKEN_HEADER = "X-FoxDesk-Token"

# Mirror the token next to the desktop shell's single-instance lock dir so
# tray actions (stop-all on quit) can authenticate against the local API.
# ACL note (verified via icacls): %TEMP% inherits the user-profile DACL —
# the file is readable only by the owning user, SYSTEM, and Administrators.
# Cross-user exposure is not a practical vector; same-user processes can
# read process memory anyway (accepted threat model, see README).
_TOKEN_FILE = Path(tempfile.gettempdir()) / "FoxDesk" / "api-token"


def _write_token_file() -> None:
    try:
        _TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        _TOKEN_FILE.write_text(API_TOKEN, encoding="utf-8")
    except Exception:
        pass


def _remove_token_file() -> None:
    try:
        _TOKEN_FILE.unlink(missing_ok=True)
    except Exception:
        pass


_write_token_file()
# Best-effort removal on interpreter exit; hard kills leave a stale token
# that is simply overwritten on the next launch.
atexit.register(_remove_token_file)

# DNS-rebinding guard: only loopback hosts may reach this app. A public DNS
# name rebound to 127.0.0.1 would otherwise be same-origin with the API and
# could read the bootstrap token injected into GET /.
_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "[::1]", "::1"}


def _is_loopback_host(host_header: str) -> bool:
    host = (host_header or "").strip().lower()
    if not host:
        return False
    if host in _LOOPBACK_HOSTS:
        return True
    # Strip a single trailing :port (but not the colons in a bare IPv6 literal).
    if host.count(":") == 1:
        host = host.rsplit(":", 1)[0]
        return host in _LOOPBACK_HOSTS
    # Bracketed IPv6 with port, e.g. [::1]:8765
    if host.startswith("[") and "]" in host:
        return host.split("]", 1)[0] + "]" in _LOOPBACK_HOSTS
    return False


class LocalApiTokenMiddleware(BaseHTTPMiddleware):
    """Require loopback Host + token for /api/* except a tiny bootstrap endpoint."""

    OPEN_PREFIXES = (
        "/assets/",
        "/favicon",
    )
    OPEN_EXACT = {
        "/",
        "/api/bootstrap",
        "/api/system/ping",
    }

    async def dispatch(self, request: Request, call_next):
        # Loopback-only Host: blocks DNS rebinding names before any handler runs.
        if not _is_loopback_host(request.headers.get("host")):
            return JSONResponse(
                status_code=421,
                content={"detail": "misdirected request: loopback host header required"},
            )
        # Cross-site browser requests are rejected outright (same-origin UI
        # fetches send no Origin header for GET).
        origin = request.headers.get("origin")
        if origin:
            try:
                from urllib.parse import urlparse

                origin_host = urlparse(origin).hostname or ""
            except Exception:
                origin_host = ""
            if origin_host not in {"127.0.0.1", "localhost", "::1"}:
                return JSONResponse(
                    status_code=403,
                    content={"detail": "cross-origin requests are not allowed"},
                )
        path = request.url.path or "/"
        if path in self.OPEN_EXACT or any(path.startswith(p) for p in self.OPEN_PREFIXES):
            return await call_next(request)
        if path.startswith("/api/"):
            provided = (
                request.headers.get(API_TOKEN_HEADER)
                or request.headers.get("x-foxdesk-token")
                or ""
            )
            if not provided or not secrets.compare_digest(provided, API_TOKEN):
                return JSONResponse(
                    status_code=401,
                    content={
                        "detail": (
                            "unauthorized: missing or invalid X-FoxDesk-Token "
                            "(local API is protected; reload the FoxDesk UI)"
                        )
                    },
                )
        return await call_next(request)
