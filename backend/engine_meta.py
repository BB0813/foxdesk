"""Pure engine/backend naming + error humanization helpers.

No I/O, no imports from other backend modules — safe for import from
core and anywhere else without cycles.
"""
from __future__ import annotations


def normalize_engine_name(value: str | None) -> str:
    raw = (value or "camoufox").strip().lower()
    if raw in {"", "firefox", "camoufox", "default"}:
        return "camoufox"
    if raw in {"chromium", "chrome", "pw", "playwright"}:
        return "chromium"
    return "camoufox"


def normalize_chromium_backend_name(value: str | None) -> str:
    raw = (value or "auto").strip().lower()
    if raw in {"", "auto", "default"}:
        return "auto"
    if raw in {"playwright", "pw"}:
        return "playwright"
    if raw in {"patchright", "pr", "patched"}:
        return "patchright"
    return "auto"


def chromium_install_hint(backend: str | None = None) -> str:
    """User-facing install commands for Chromium stack gaps."""
    name = normalize_chromium_backend_name(backend)
    if name == "patchright":
        return "pip install patchright && patchright install chromium"
    if name == "playwright":
        return "pip install playwright && playwright install chromium"
    # auto / both
    return (
        "pip install playwright patchright && "
        "playwright install chromium && patchright install chromium"
    )


def humanize_chromium_launch_error(exc: BaseException | str, backend: str | None = None) -> str:
    """Map Playwright/Patchright launch failures to actionable install text."""
    text = str(exc)
    low = text.lower()
    be = normalize_chromium_backend_name(backend) if backend else "auto"
    hint_pr = "patchright install chromium"
    hint_pw = "playwright install chromium"
    hint = hint_pr if be == "patchright" else (hint_pw if be == "playwright" else f"{hint_pw}  (or {hint_pr})")
    if any(
        key in low
        for key in (
            "executable doesn't exist",
            "browser not found",
            "browsers are not installed",
            "please run the following command to download",
            "chromium distribution is not found",
            "browserType.launch",
            "browser_type.launch",
        )
    ) or ("chromium" in low and "install" in low):
        return (
            f"Chromium browser binary missing for backend={be}. "
            f"Run: {hint}. "
            f"Full stack: {chromium_install_hint(be)}. "
            f"Detail: {text}"
        )
    if "channel" in low and "chrome" in low:
        return (
            "chromium_channel=chrome failed — install Google Chrome or clear channel to use bundled Chromium. "
            f"Detail: {text}"
        )
    if "patchright" in low and "not installed" in low:
        return f"patchright package missing. Run: {chromium_install_hint('patchright')}. Detail: {text}"
    if "playwright" in low and "not installed" in low:
        return f"playwright package missing. Run: {chromium_install_hint('playwright')}. Detail: {text}"
    return text
