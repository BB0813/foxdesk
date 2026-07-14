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


def format_http_error(exc: BaseException) -> str:
    """Human-readable HTTP / network errors (especially GitHub 403 rate limit)."""
    if isinstance(exc, urllib.error.HTTPError):
        code = exc.code
        reason = (exc.reason or "").strip()
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="replace")[:400]
        except Exception:
            body = ""
        low = f"{reason} {body}".lower()
        if code == 403 and ("rate limit" in low or "api rate limit" in low or "rate_limit" in low):
            return (
                "GitHub API 请求过于频繁（未登录每小时约 60 次限制）。"
                "请稍后再试；应用会自动改用网页/Atom 回退通道。"
            )
        if code == 403:
            return f"GitHub 拒绝访问 (HTTP 403): {reason or body or 'forbidden'}"
        if code == 404:
            return "未找到 Release（仓库或标签不存在）"
        return f"HTTP Error {code}: {reason or body or 'request failed'}"
    if isinstance(exc, urllib.error.URLError):
        return f"网络错误: {exc.reason}"
    return str(exc)


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
    # Avoid hammering api.github.com (unauthenticated limit is ~60/hour/IP).
    CHECK_CACHE_SECONDS = 120

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
        self._check_cache: dict[str, Any] | None = None
        self._check_cache_at: float = 0.0
        self._check_cache_pre: bool | None = None
        self.download_dir.mkdir(parents=True, exist_ok=True)

    def status(self) -> dict[str, Any]:
        with self.lock:
            return self.state.view()

    def _log(self, line: str) -> None:
        with self.lock:
            self.state.logs.append(line)
            if len(self.state.logs) > 200:
                self.state.logs = self.state.logs[-200:]

    def _open_url(self, url: str, *, accept: str, timeout: float = 12.0):
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": accept,
            },
        )
        return urllib.request.urlopen(req, timeout=timeout)

    def _request_json(self, url: str, timeout: float = 12.0, *, accept: str | None = None) -> Any:
        try:
            with self._open_url(
                url,
                accept=accept or "application/vnd.github+json, application/json",
                timeout=timeout,
            ) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise RuntimeError(format_http_error(exc)) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(format_http_error(exc)) from exc

    def _request_text(self, url: str, timeout: float = 12.0) -> str:
        try:
            with self._open_url(
                url,
                accept="text/plain, application/octet-stream, application/atom+xml, */*",
                timeout=timeout,
            ) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            raise RuntimeError(format_http_error(exc)) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(format_http_error(exc)) from exc

    def _synthetic_assets(self, tag: str) -> list[dict[str, Any]]:
        """Build download URLs without api.github.com asset metadata."""
        version = tag.lstrip("v")
        base = f"https://github.com/{self.github_repo}/releases/download/v{version}"
        setup = f"FoxDesk-{version}-Setup.exe"
        return [
            {
                "name": setup,
                "browser_download_url": f"{base}/{setup}",
                "size": 0,
            },
            {
                "name": "SHA256SUMS",
                "browser_download_url": f"{base}/SHA256SUMS",
                "size": 0,
            },
        ]

    def _release_from_web_latest(self) -> dict[str, Any] | None:
        # github.com/.../releases/latest with Accept: application/json returns tag_name
        # and does not share api.github.com's unauthenticated rate limit bucket.
        data = self._request_json(
            f"https://github.com/{self.github_repo}/releases/latest",
            accept="application/json",
        )
        if not isinstance(data, dict):
            return None
        tag = (data.get("tag_name") or "").strip()
        if not tag:
            return None
        version = tag.lstrip("v")
        return {
            "tag_name": tag,
            "name": data.get("name") or f"FoxDesk {version}",
            "html_url": f"https://github.com/{self.github_repo}/releases/tag/{tag}",
            "prerelease": bool(data.get("prerelease", False)),
            "assets": self._synthetic_assets(version),
            "_source": "github_web_latest",
        }

    def _release_from_atom(self, *, include_prerelease: bool) -> dict[str, Any] | None:
        xml = self._request_text(f"https://github.com/{self.github_repo}/releases.atom")
        # Prefer stable tags when not on a beta channel.
        entries = re.findall(
            r"<entry>\s*<id>([^<]+)</id>.*?<title>([^<]*)</title>",
            xml,
            flags=re.S | re.I,
        )
        best: dict[str, Any] | None = None
        best_tag: str | None = None
        for entry_id, title in entries:
            m = re.search(r"/([^/]+)$", entry_id.strip())
            if not m:
                continue
            tag = m.group(1).strip()
            version = tag.lstrip("v")
            if not version:
                continue
            _, pre = parse_version(version)
            if pre and not include_prerelease:
                continue
            if best is None or version_is_newer(version, best_tag or "0"):
                best_tag = version
                best = {
                    "tag_name": tag if tag.startswith("v") else f"v{version}",
                    "name": (title or "").strip() or f"FoxDesk {version}",
                    "html_url": f"https://github.com/{self.github_repo}/releases/tag/v{version}",
                    "prerelease": bool(pre),
                    "assets": self._synthetic_assets(version),
                    "_source": "github_atom",
                }
        return best

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

    def _select_release_api(self, include_prerelease: bool) -> dict[str, Any] | None:
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
            if best is not None:
                best = dict(best)
                best["_source"] = "github_api"
            return best
        data = self._request_json(f"https://api.github.com/repos/{self.github_repo}/releases/latest")
        if isinstance(data, dict):
            data = dict(data)
            data["_source"] = "github_api"
        return data

    def _select_release(self, include_prerelease: bool) -> dict[str, Any] | None:
        errors: list[str] = []

        # 1) Official API (rich asset metadata)
        try:
            data = self._select_release_api(include_prerelease)
            if data:
                self._log(f"release source=github_api tag={data.get('tag_name')}")
                return data
        except Exception as exc:
            msg = format_http_error(exc)
            errors.append(f"api: {msg}")
            self._log(f"api release lookup failed: {msg}")

        # 2) github.com web JSON (latest stable; avoids API rate limit)
        if not include_prerelease:
            try:
                data = self._release_from_web_latest()
                if data:
                    self._log(f"release source=github_web_latest tag={data.get('tag_name')}")
                    return data
            except Exception as exc:
                msg = format_http_error(exc)
                errors.append(f"web: {msg}")
                self._log(f"web latest lookup failed: {msg}")

        # 3) Atom feed (works for stable + prerelease tags)
        try:
            data = self._release_from_atom(include_prerelease=include_prerelease)
            if data:
                self._log(f"release source=github_atom tag={data.get('tag_name')}")
                return data
        except Exception as exc:
            msg = format_http_error(exc)
            errors.append(f"atom: {msg}")
            self._log(f"atom lookup failed: {msg}")

        if errors:
            raise RuntimeError("；".join(errors))
        return None

    def check(self, *, include_prerelease: bool | None = None, force: bool = False) -> dict[str, Any]:
        use_pre = prefer_prereleases(self.app_version) if include_prerelease is None else include_prerelease

        with self.lock:
            if self.state.status == "downloading":
                return self.state.view()
            # Short in-process cache: clicking "检查更新" twice shouldn't burn API quota.
            if (
                not force
                and self._check_cache is not None
                and self._check_cache_pre is use_pre
                and (time.time() - self._check_cache_at) < self.CHECK_CACHE_SECONDS
                and self.state.status in {"available", "up_to_date", "ready"}
            ):
                self._log("check served from cache")
                return self.state.view()

            self.state.status = "checking"
            self.state.error = None
            self.state.current = self.app_version
            self.state.expected_sha256 = None
            self.state.actual_sha256 = None
            self.state.sha256_verified = None
            self.state.checksum_url = None

        try:
            data = self._select_release(include_prerelease=use_pre)
            if not data:
                raise RuntimeError("no releases found")
            tag = (data.get("tag_name") or "").lstrip("v")
            html_url = data.get("html_url") or f"https://github.com/{self.github_repo}/releases"
            assets = data.get("assets") or []
            # Fallback channels only know the tag; synthesize conventional asset URLs.
            if not assets and tag:
                assets = self._synthetic_assets(tag)
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
                    self._log(f"checksum fetch failed: {format_http_error(exc)}")
                    # If API was rate-limited, try the conventional download URL.
                    if asset and not expected:
                        version = tag.lstrip("v")
                        alt = (
                            f"https://github.com/{self.github_repo}/releases/download/"
                            f"v{version}/SHA256SUMS"
                        )
                        if alt != checksum_url:
                            try:
                                text = self._request_text(alt, timeout=15)
                                mapping = parse_sha256sums(text)
                                expected = mapping.get((asset.get("name") or "").lower())
                                if expected:
                                    checksum_url = alt
                                    self._log(f"checksum loaded via direct URL entries={len(mapping)}")
                            except Exception as exc2:
                                self._log(f"checksum direct fetch failed: {format_http_error(exc2)}")
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
                    f"sha256={'yes' if expected else 'no'} source={data.get('_source')}"
                )
                view = self.state.view()
                self._check_cache = view
                self._check_cache_at = time.time()
                self._check_cache_pre = use_pre
                return view
        except Exception as exc:
            with self.lock:
                self.state.status = "failed"
                self.state.error = format_http_error(exc)
                self.state.checked_at = time.time()
                self._log(f"check failed: {self.state.error}")
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
