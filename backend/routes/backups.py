"""Backup routes: encrypted .fdk create / list / restore."""
from __future__ import annotations

import hashlib
import json
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from backend.backup_util import collect_backup_files, safe_restore_target
from backend.core import APP_VERSION, DATA_DIR, activity, now_iso, registry
from backend.models import BackupRequest, BackupRestoreRequest
from backend.storage_util import atomic_write_text

router = APIRouter()


@router.get("/api/system/backups")
def list_backups() -> dict[str, Any]:
    backups = DATA_DIR / "backups"
    backups.mkdir(parents=True, exist_ok=True)
    items: list[dict[str, Any]] = []
    for p in sorted(backups.glob("foxdesk-backup-*"), reverse=True):
        if not p.is_file():
            continue
        try:
            st = p.stat()
            kind = "encrypted" if p.suffix.lower() == ".fdk" else ("zip" if p.suffix.lower() == ".zip" else "file")
            items.append(
                {
                    "name": p.name,
                    "path": str(p),
                    "size": st.st_size,
                    "mtime": st.st_mtime,
                    "kind": kind,
                }
            )
        except OSError:
            continue
    return {"ok": True, "items": items[:100], "dir": str(backups)}


@router.post("/api/system/backup")
def create_encrypted_backup(request: BackupRequest) -> dict[str, Any]:
    """Export core config into a password-encrypted `.fdk` package under data_dir/backups."""
    from backend.backup_crypto import write_encrypted_backup

    backups = DATA_DIR / "backups"
    backups.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = backups / f"foxdesk-backup-{stamp}.fdk"
    files = collect_backup_files(include_profiles_dirs=request.include_profiles_dirs)
    if not files:
        raise HTTPException(status_code=400, detail="nothing to back up")
    meta = {
        "app_version": APP_VERSION,
        "created_at": now_iso(),
        "files": sorted(files.keys()),
        "format": "foxdesk-backup-v1",
        "note": "Password-based encrypt-then-MAC package (PBKDF2 + HMAC). Keep offline.",
    }
    try:
        write_encrypted_backup(out_path, request.password, files, meta)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    activity.log("backup_create", str(out_path))
    return {
        "ok": True,
        "path": str(out_path),
        "files": meta["files"],
        "format": "fdk",
        "warning": "Store the password safely. Wrong password cannot recover this file.",
    }


@router.post("/api/system/backup/restore")
def restore_encrypted_backup(request: BackupRestoreRequest) -> dict[str, Any]:
    """Restore a password-encrypted `.fdk` backup (or legacy integrity zip) into data_dir.

    Running sessions should be stopped first. Creates a pre-restore snapshot under backups/.
    """
    from backend.backup_crypto import read_encrypted_backup, write_encrypted_backup

    if registry.running_session_count() > 0:
        raise HTTPException(
            status_code=409,
            detail="stop all running sessions before restoring a backup",
        )

    path = Path(request.path).expanduser()
    if not path.is_absolute():
        path = (DATA_DIR / "backups" / path.name).resolve()
    else:
        path = path.resolve()
    backups_dir = (DATA_DIR / "backups").resolve()
    try:
        path.relative_to(DATA_DIR.resolve())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="backup path must be under data directory") from exc
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="backup file not found")

    files: dict[str, bytes] = {}
    meta: dict[str, Any] = {}
    try:
        meta, files = read_encrypted_backup(path, request.password)
    except ValueError as exc:
        msg = str(exc)
        if msg == "legacy_or_plain_zip" and path.suffix.lower() == ".zip":
            try:
                with zipfile.ZipFile(path, "r") as zf:
                    names = zf.namelist()
                    if "backup-meta.json" in names:
                        meta = json.loads(zf.read("backup-meta.json").decode("utf-8"))
                        # Accepted risk (legacy format only): the stored
                        # unsalted SHA256 is an offline cracking oracle, but
                        # legacy zips are also unencrypted/unauthenticated, so
                        # the user must already fully trust the file. New
                        # backups use the AEAD-style .fdk format.
                        stamp = str(meta.get("password_sha256") or "")
                        if stamp and hashlib.sha256(request.password.encode("utf-8")).hexdigest() != stamp:
                            raise HTTPException(status_code=400, detail="wrong password for legacy backup")
                    for name in names:
                        if name.endswith("/") or name == "backup-meta.json":
                            continue
                        files[name.replace("\\", "/")] = zf.read(name)
            except HTTPException:
                raise
            except Exception as zip_exc:
                raise HTTPException(status_code=400, detail=f"invalid legacy zip: {zip_exc}") from zip_exc
        elif "wrong password" in msg or "corrupted" in msg:
            raise HTTPException(status_code=400, detail="wrong password or corrupted backup") from exc
        else:
            raise HTTPException(status_code=400, detail=msg) from exc

    if not files:
        raise HTTPException(status_code=400, detail="backup contains no files")

    wanted = {n.strip() for n in (request.include or []) if n and n.strip()}
    restored: list[str] = []
    skipped: list[str] = []

    snap_path = None
    try:
        snap_files = collect_backup_files(include_profiles_dirs=False)
        if snap_files:
            snap_path = backups_dir / f"pre-restore-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.fdk"
            write_encrypted_backup(
                snap_path,
                request.password,
                snap_files,
                {"app_version": APP_VERSION, "created_at": now_iso(), "note": "auto pre-restore snapshot"},
            )
    except Exception:
        snap_path = None

    for arcname, data in files.items():
        if wanted and arcname not in wanted and not any(arcname.startswith(w.rstrip("/") + "/") for w in wanted):
            skipped.append(arcname)
            continue
        target = safe_restore_target(arcname)
        if target is None:
            skipped.append(arcname)
            continue
        if not request.overwrite and target.exists():
            skipped.append(arcname)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.suffix.lower() == ".json":
            try:
                text_out = data.decode("utf-8")
            except UnicodeDecodeError:
                text_out = data.decode("utf-8", errors="replace")
            atomic_write_text(target, text_out)
        else:
            tmp = target.with_name(f".{target.name}.{os.getpid()}.tmp")
            tmp.write_bytes(data)
            tmp.replace(target)
        restored.append(arcname)

    activity.log("backup_restore", f"path={path.name} restored={len(restored)} skipped={len(skipped)}")
    return {
        "ok": True,
        "path": str(path),
        "restored": restored,
        "skipped": skipped,
        "meta": meta,
        "pre_restore_snapshot": str(snap_path) if snap_path else None,
        "note": "JSON stores re-read on next API call; restart app if UI looks stale.",
    }
