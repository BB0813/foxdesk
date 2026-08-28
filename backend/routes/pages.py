"""UI shell + bootstrap endpoints."""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from backend.core import APP_VERSION, STATIC_DIR
from backend.local_auth import API_TOKEN, API_TOKEN_HEADER

router = APIRouter()


@router.get("/")
def index() -> HTMLResponse:
    """Serve UI shell with per-process API token injected."""
    html_path = STATIC_DIR / "index.html"
    html = html_path.read_text(encoding="utf-8")
    bootstrap = (
        "<script>"
        f"window.__FOXDESK_BOOT__={json.dumps({'token': API_TOKEN, 'version': APP_VERSION})};"
        "</script>"
    )
    if "</head>" in html:
        html = html.replace("</head>", bootstrap + "\n  </head>", 1)
    else:
        html = bootstrap + html
    return HTMLResponse(content=html)


@router.get("/api/bootstrap")
def api_bootstrap() -> dict[str, Any]:
    """Public bootstrap metadata for UI clients."""
    return {
        "ok": True,
        "app_name": "FoxDesk",
        "app_version": APP_VERSION,
        "token_header": API_TOKEN_HEADER,
        "auth_required": True,
        "note": "Use the token injected into index.html (window.__FOXDESK_BOOT__).",
    }
