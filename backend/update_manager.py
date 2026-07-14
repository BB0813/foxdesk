from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def parse_version(value: str) -> tuple[tuple[int, ...], str]:
    """Return ((major, minor, patch, ...), prerelease) for ordering."""
    raw = (value or "").strip().lstrip("vV")
    if not raw:
        return (0,), ""
    main, _, pre = raw.partition("-")
    parts: list[int] = []
    for chunk in main.split("."):
        m = re.match(r"(\d+)", chunk)
        parts.append(int(m.group(1)) if m else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts), pre.lower()


def version_is_newer(candidate: str, current: str) -> bool:
    c_main, c_pre = parse_version(candidate)
    u_main, u_pre = parse_version(current)
    if c_main != u_main:
        return c_main > u_main
    # Same numeric core: release (no pre) > prerelease; compare pre tags lexicographically otherwise.
    if not c_pre and u_pre:
        return True
    if c_pre and not u_pre:
        return False
    if c_pre and u_pre:
        return c_pre > u_pre
    return False


def prefer_prereleases(current: str) -> bool:
    _, pre = parse_version(current)
    return bool(pre)


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def parse_sha256sums(text: str) -> dict[str, str]:
    """Parse `SHA256  filename` or `SHA256 *filename` lines."""
    mapping: dict[str, str] = {}
    for line in (text or "").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # GNU coreutils: "<hash>  <name>" or "<hash> *<name>"
        m = re.match(r"^([A-Fa-f0-9]{64})\s+\*?(.+)$", line)
        if not m:
            continue
        digest, name = m.group(1).lower(), m.group(2).strip().strip('"')
        mapping[Path(name).name.lower()] = digest
    return mapping


@dataclass
class UpdateState:
    status: str = "idle"  # idle | checking | available | downloading | ready | installing | failed | up_to_date
    current: str = ""
    latest: str | None = None
    release_name: str | None = None
    release_url: str | None = None
    prerelease: bool = False
    asset_name: str | None = None
    asset_url: str | None = None
    asset_size: int | None = None
    checksum_url: str | None = None
    expected_sha256: str | None = None
    actual_sha256: str | None = None
    sha256_verified: bool | None = None
    downloaded_bytes: int = 0
    progress: int = 0
    local_path: str | None = None
    error: str | None = None
    checked_at: float | None = None
    logs: list[str] = field(default_factory=list)

    def view(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "current": self.current,
            "latest": self.latest,
            "release_name": self.release_name,
            "release_url": self.release_url,
            "prerelease": self.prerelease,
            "asset_name": self.asset_name,
            "asset_url": self.asset_url,
            "asset_size": self.asset_size,
            "checksum_url": self.checksum_url,
            "expected_sha256": self.expected_sha256,
            "actual_sha256": self.actual_sha256,
            "sha256_verified": self.sha256_verified,
            "downloaded_bytes": self.downloaded_bytes,
            "progress": self.progress,
            "local_path": self.local_path,
            "error": self.error,
            "checked_at": self.checked_at,
            "logs": self.logs[-80:],
            "update_available": self.status in {"available", "downloading", "ready", "installing"}
            or (self.latest is not None and version_is_newer(self.latest, self.current)),
            "can_one_click": bool(self.asset_url) and os.name == "nt",
        }


class UpdateManager:
    def __init__(
        self,
        *,
        app_version: str,
        github_repo: str,
        download_dir: Path,
        user_agent: str,
        require_checksum: bool = False,
    ) -> None:
        self.app_version = app_version
        self.github_repo = github_repo
        self.download_dir = Path(download_dir)
        self.user_agent = user_agent
        # When True, refuse install if SHA256SUMS is missing/mismatched.
        self.require_checksum = require_checksum
        self.lock = threading.RLock()
        self.state = UpdateState(current=app_version)
        self._thread: threading.Thread | None = None
        self.download_dir.mkdir(parents=True, exist_ok=True)

    def status(self) -> dict[str, Any]:
        with self.lock:
            return self.state.view()

    def _log(self, line: str) -> None:
        with self.lock:
            self.state.logs.append(line)
            if len(self.state.logs) > 200:
                self.state.logs = self.state.logs[-200:]

    def _request_json(self, url: str, timeout: float = 12.0) -> Any:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "application/vnd.github+json",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _request_text(self, url: str, timeout: float = 12.0) -> str:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "text/plain, application/octet-stream, */*",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")

    def _pick_setup_asset(self, assets: list[dict[str, Any]]) -> dict[str, Any] | None:
        preferred: list[dict[str, Any]] = []
        for asset in assets or []:
            name = (asset.get("name") or "").lower()
            if not name.endswith(".exe"):
                continue
            if "setup" in name or name.startswith("foxdesk"):
                preferred.append(asset)
        if preferred:
            preferred.sort(key=lambda a: (0 if "setup" in (a.get("name") or "").lower() else 1, a.get("name") or ""))
            return preferred[0]
        return None

    def _pick_checksum_asset(self, assets: list[dict[str, Any]]) -> dict[str, Any] | None:
        for asset in assets or []:
            name = (asset.get("name") or "").lower()
            if name in {"sha256sums", "sha256sums.txt", "checksums.txt", "checksums.sha256"}:
                return asset
            if name.endswith(".sha256") or name.endswith(".sha256.txt"):
                return asset
        return None

    def _select_release(self, include_prerelease: bool) -> dict[str, Any] | None:
        if include_prerelease:
            releases = self._request_json(
                f"https://api.github.com/repos/{self.github_repo}/releases?per_page=15"
            )
            if not isinstance(releases, list):
                return None
            best = None
            best_tag = None
            for rel in releases:
                if rel.get("draft"):
                    continue
                tag = (rel.get("tag_name") or "").lstrip("v")
                if not tag:
                    continue
                if best is None or version_is_newer(tag, best_tag or "0"):
                    best = rel
                    best_tag = tag
            return best
        return self._request_json(f"https://api.github.com/repos/{self.github_repo}/releases/latest")

    def check(self, *, include_prerelease: bool | None = None) -> dict[str, Any]:
        with self.lock:
            if self.state.status == "downloading":
                return self.state.view()
            self.state.status = "checking"
            self.state.error = None
            self.state.current = self.app_version
            self.state.expected_sha256 = None
            self.state.actual_sha256 = None
            self.state.sha256_verified = None
            self.state.checksum_url = None

        use_pre = prefer_prereleases(self.app_version) if include_prerelease is None else include_prerelease
        try:
            data = self._select_release(include_prerelease=use_pre)
            if not data:
                raise RuntimeError("no releases found")
            tag = (data.get("tag_name") or "").lstrip("v")
            html_url = data.get("html_url") or f"https://github.com/{self.github_repo}/releases"
            assets = data.get("assets") or []
            asset = self._pick_setup_asset(assets)
            checksum_asset = self._pick_checksum_asset(assets)
            expected = None
            checksum_url = None
            if checksum_asset and asset:
                checksum_url = checksum_asset.get("browser_download_url")
                try:
                    text = self._request_text(checksum_url, timeout=15)
                    mapping = parse_sha256sums(text)
                    expected = mapping.get((asset.get("name") or "").lower())
                    if not expected and len(mapping) == 1:
                        expected = next(iter(mapping.values()))
                    self._log(f"checksum asset loaded entries={len(mapping)}")
                except Exception as exc:
                    self._log(f"checksum fetch failed: {exc}")
            newer = version_is_newer(tag, self.app_version) if tag else False
            with self.lock:
                self.state.latest = tag
                self.state.release_name = data.get("name") or tag
                self.state.release_url = html_url
                self.state.prerelease = bool(data.get("prerelease"))
                self.state.checked_at = time.time()
                self.state.checksum_url = checksum_url
                self.state.expected_sha256 = expected
                if asset:
                    self.state.asset_name = asset.get("name")
                    self.state.asset_url = asset.get("browser_download_url")
                    self.state.asset_size = int(asset.get("size") or 0) or None
                else:
                    self.state.asset_name = None
                    self.state.asset_url = None
                    self.state.asset_size = None
                if newer:
                    self.state.status = "available"
                    if self.state.local_path and Path(self.state.local_path).exists() and self.state.asset_name:
                        if Path(self.state.local_path).name == self.state.asset_name:
                            # re-verify existing download if possible
                            try:
                                self._verify_local_file(Path(self.state.local_path))
                                self.state.status = "ready"
                                self.state.progress = 100
                            except Exception as exc:
                                self._log(f"existing download invalid: {exc}")
                                self.state.local_path = None
                else:
                    self.state.status = "up_to_date"
                    self.state.progress = 0
                    self.state.local_path = None
                self._log(
                    f"checked latest={tag} newer={newer} asset={self.state.asset_name} "
                    f"sha256={'yes' if expected else 'no'}"
                )
                return self.state.view()
        except Exception as exc:
            with self.lock:
                self.state.status = "failed"
                self.state.error = str(exc)
                self.state.checked_at = time.time()
                self._log(f"check failed: {exc}")
                return self.state.view()

    def _verify_local_file(self, path: Path) -> None:
        digest = sha256_file(path)
        with self.lock:
            self.state.actual_sha256 = digest
            expected = self.state.expected_sha256
        if expected:
            if digest.lower() != expected.lower():
                with self.lock:
                    self.state.sha256_verified = False
                raise RuntimeError(
                    f"SHA256 mismatch for {path.name}: expected {expected}, got {digest}"
                )
            with self.lock:
                self.state.sha256_verified = True
            self._log(f"sha256 verified: {digest[:16]}…")
        else:
            with self.lock:
                self.state.sha256_verified = None
            if self.require_checksum:
                raise RuntimeError("Release has no SHA256SUMS; refusing to install")
            self._log("sha256: no checksum published for this release (skipped)")

    def start_download(self) -> dict[str, Any]:
        with self.lock:
            if self.state.status == "downloading":
                return self.state.view()
        info = self.check()
        if not info.get("update_available"):
            return info
        if not info.get("asset_url"):
            with self.lock:
                self.state.status = "failed"
                self.state.error = "No Windows installer asset found on release"
                return self.state.view()
        with self.lock:
            if self.state.status == "ready" and self.state.local_path and Path(self.state.local_path).exists():
                return self.state.view()
            self.state.status = "downloading"
            self.state.progress = 0
            self.state.downloaded_bytes = 0
            self.state.error = None
            self.state.actual_sha256 = None
            self.state.sha256_verified = None
            self._thread = threading.Thread(target=self._download_worker, daemon=True)
            self._thread.start()
            return self.state.view()

    def _download_worker(self) -> None:
        with self.lock:
            url = self.state.asset_url
            name = self.state.asset_name or "FoxDesk-Setup.exe"
            expected = self.state.asset_size
        if not url:
            with self.lock:
                self.state.status = "failed"
                self.state.error = "missing asset url"
            return
        target = self.download_dir / name
        tmp = target.with_suffix(target.suffix + ".part")
        try:
            self._log(f"downloading {url}")
            req = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
            with urllib.request.urlopen(req, timeout=60) as resp, open(tmp, "wb") as fh:
                total = expected or int(resp.headers.get("Content-Length") or 0) or None
                downloaded = 0
                while True:
                    chunk = resp.read(1024 * 256)
                    if not chunk:
                        break
                    fh.write(chunk)
                    downloaded += len(chunk)
                    with self.lock:
                        self.state.downloaded_bytes = downloaded
                        if total:
                            self.state.progress = max(0, min(99, int(downloaded * 100 / total)))
                        else:
                            self.state.progress = min(99, self.state.progress + 1)
            tmp.replace(target)
            self._verify_local_file(target)
            with self.lock:
                self.state.local_path = str(target)
                self.state.progress = 100
                self.state.status = "ready"
                self.state.error = None
            self._log(f"download ready: {target}")
        except Exception as exc:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
            try:
                if target.exists():
                    target.unlink(missing_ok=True)
            except OSError:
                pass
            with self.lock:
                self.state.status = "failed"
                self.state.error = str(exc)
                self.state.local_path = None
            self._log(f"download failed: {exc}")

    def install(self, *, exit_after: bool = True) -> dict[str, Any]:
        with self.lock:
            path = self.state.local_path
            if not path or not Path(path).exists():
                return {
                    **self.state.view(),
                    "ok": False,
                    "error": self.state.error or "Installer not downloaded yet",
                }
            installer = Path(path)
            # Final integrity gate before exec
            try:
                self._verify_local_file(installer)
            except Exception as exc:
                self.state.status = "failed"
                self.state.error = str(exc)
                return {**self.state.view(), "ok": False}
            self.state.status = "installing"
            self._log(f"launching installer: {installer}")

        if os.name != "nt":
            with self.lock:
                self.state.status = "failed"
                self.state.error = "One-click update is only supported on Windows"
                return {**self.state.view(), "ok": False}

        try:
            creationflags = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
            subprocess.Popen(
                [str(installer)],
                cwd=str(installer.parent),
                close_fds=True,
                creationflags=creationflags,
            )
            with self.lock:
                self.state.status = "installing"
                self.state.error = None
            result = {**self.status(), "ok": True, "exit_after": exit_after}
            if exit_after:
                threading.Thread(target=self._delayed_exit, daemon=True).start()
            return result
        except Exception as exc:
            with self.lock:
                self.state.status = "failed"
                self.state.error = str(exc)
            return {**self.state.view(), "ok": False}

    def _delayed_exit(self) -> None:
        time.sleep(1.2)
        os._exit(0)
