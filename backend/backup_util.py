"""Backup archive helpers: file collection and restore-target sanitization."""
from __future__ import annotations

import os
from pathlib import Path, PurePosixPath, PureWindowsPath

from backend.core import DATA_DIR, PROFILES_DIR

_BACKUP_SAFE_ROOT_NAMES = {
    "profiles.json",
    "proxies.json",
    "settings.json",
    "channels.json",
    "activity.json",
}


def collect_backup_files(*, include_profiles_dirs: bool) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    for name in sorted(_BACKUP_SAFE_ROOT_NAMES):
        p = DATA_DIR / name
        if p.exists() and p.is_file():
            files[name] = p.read_bytes()
    if include_profiles_dirs and PROFILES_DIR.exists():
        for p in PROFILES_DIR.rglob("*"):
            if not p.is_file():
                continue
            if p.stat().st_size > 8 * 1024 * 1024:
                continue
            rel = p.relative_to(PROFILES_DIR)
            if ".." in rel.parts:
                continue
            arc = str(Path("profiles") / rel).replace("\\", "/")
            files[arc] = p.read_bytes()
    return files


def safe_restore_target(arcname: str) -> Path | None:
    """Map archive name to absolute path under DATA_DIR, or None if unsafe.

    Must reject not only ``..`` traversal but Windows drive-absolute
    (``C:/x``), root-absolute (``/x`` → drive root) and UNC (``//server/x``)
    arcnames — pathlib joins replace the base entirely for those.
    """
    name = (arcname or "").replace("\\", "/").lstrip("/")
    if not name or name.startswith("../") or "/../" in f"/{name}/":
        return None
    if name in _BACKUP_SAFE_ROOT_NAMES:
        return DATA_DIR / name
    if name.startswith("profiles/"):
        rel = name[len("profiles/") :]
        rel_path = PureWindowsPath(rel) if os.name == "nt" else PurePosixPath(rel)
        if not rel or rel_path.drive or rel_path.root or ".." in rel_path.parts:
            return None
        target = (PROFILES_DIR / rel).resolve()
        try:
            target.relative_to(PROFILES_DIR.resolve())
        except ValueError:
            return None
        return target
    return None
