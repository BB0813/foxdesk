"""Xray Bridge plugin: vless tunnel nodes -> local SOCKS5 via xray-core.

The core binary is resolved from (1) settings xray_path, (2) PATH,
(3) this plugin's bin/ directory. If missing, ``download_core`` fetches the
official Xray-core Windows release and verifies it against the release
SHA256 digest before extracting xray.exe.
"""
from __future__ import annotations

import hashlib
import sys
import json
import re
import shutil
import zipfile
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

XRAY_REPO = "https://api.github.com/repos/XTLS/Xray-core/releases/latest"

# Platform -> asset name in the Xray-core release
XRAY_ASSETS = {
    ("win32", "amd64"): "Xray-windows-64.zip",
    ("linux", "x86_64"): "Xray-linux-64.zip",
    ("linux", "aarch64"): "Xray-linux-arm64-v8a.zip",
    ("darwin", "x86_64"): "Xray-macos-64.zip",
    ("darwin", "arm64"): "Xray-macos-arm64-v8a.zip",
}


def _platform_asset() -> str:
    import platform

    key = (sys.platform, platform.machine().lower())
    if sys.platform == "win32":
        key = ("win32", "amd64")
    return XRAY_ASSETS.get(key, "Xray-windows-64.zip")


class XrayBridgePlugin:
    def __init__(self, ctx) -> None:
        self.ctx = ctx
        self._bridges: dict[str, dict[str, Any]] = {}

    # ---- core binary management ----
    @property
    def bin_dir(self) -> Path:
        d = self.ctx.plugin_dir / "bin"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def xray_exe(self) -> Path:
        import sys as _sys

        name = "xray.exe" if _sys.platform == "win32" else "xray"
        return self.bin_dir / name

    def _resolve_binary(self) -> str:
        configured = str(self.ctx.get_setting("xray_path", "") or "").strip()
        candidates = []
        if configured:
            candidates.append(Path(configured))
        candidates.append(self.xray_exe)
        for c in candidates:
            if c.is_file():
                return str(c)
        import shutil

        found = shutil.which("xray") or shutil.which("xray.exe")
        if found:
            return found
        return ""

    def core_state(self) -> dict[str, Any]:
        resolved = self._resolve_binary()
        return {
            "binary": resolved or None,
            "ready": bool(resolved),
            "bin_dir": str(self.bin_dir),
        }

    def info(self) -> dict[str, Any]:
        state = self.core_state()
        running = [
            {"node_id": nid, "port": b["port"]}
            for nid, b in self._bridges.items()
            if b["proc"].poll() is None
        ]
        return {"core": state, "bridges": running}

    def download_core(self, timeout: float = 300.0) -> dict[str, Any]:
        """Download the official Xray-core release zip + digest, verify, extract."""
        import urllib.request

        req = Request(XRAY_REPO, headers={"User-Agent": "FoxDesk/xray-bridge", "Accept": "application/vnd.github+json"})
        with urlopen(req, timeout=30) as resp:
            release = json.loads(resp.read().decode("utf-8"))
        assets = {a.get("name"): a for a in release.get("assets") or []}
        asset_name = _platform_asset()
        zip_asset = assets.get(asset_name)
        dgst_asset = assets.get(asset_name + ".dgst")
        if not zip_asset or not dgst_asset:
            return {"ok": False, "error": f"release assets not found ({asset_name} for this platform)"}
        url = zip_asset.get("browser_download_url") or ""
        dgst_url = dgst_asset.get("browser_download_url") or ""
        if not url.startswith("https://github.com/"):
            return {"ok": False, "error": "unexpected download host"}
        self.ctx.log("downloading xray core...")
        zip_path = self.bin_dir / asset_name
        with urlopen(Request(url, headers={"User-Agent": "FoxDesk/xray-bridge"}), timeout=timeout) as resp, open(zip_path, "wb") as fh:
            while True:
                chunk = resp.read(1024 * 256)
                if not chunk:
                    break
                fh.write(chunk)
        with urlopen(Request(dgst_url, headers={"User-Agent": "FoxDesk/xray-bridge"}), timeout=30) as resp:
            dgst_text = resp.read().decode("utf-8", errors="replace")
        expected = None
        m = re.search(r"SHA2-256=\s*([0-9a-fA-F]{64})", dgst_text)
        if m:
            expected = m.group(1).lower()
        else:
            for token in re.findall(r"[0-9a-fA-F]{64}", dgst_text):
                expected = token.lower()
                break
        actual = hashlib.sha256(zip_path.read_bytes()).hexdigest()
        if not expected or actual != expected:
            zip_path.unlink(missing_ok=True)
            return {"ok": False, "error": f"SHA256 mismatch (expected {expected}, got {actual})"}
        import sys as _sys

        exe_name = "xray.exe" if _sys.platform == "win32" else "xray"
        target = self.bin_dir / exe_name
        with zipfile.ZipFile(zip_path) as zf:
            for name in zf.namelist():
                if name.split("/")[-1].lower() == exe_name:
                    target.write_bytes(zf.read(name))
                    break
        if _sys.platform != "win32":
            import os as _os

            target.chmod(0o755)
        zip_path.unlink(missing_ok=True)
        ok = target.is_file()
        self.ctx.log(f"xray core {'installed' if ok else 'extraction failed'}")
        return {"ok": ok, "binary": str(target) if ok else None}

    # ---- tunnel handler protocol (core extension point) ----
    def ensure_bridge(self, node_id: str, node: dict[str, Any]) -> int:
        from backend.plugin_system import spawn_and_wait_port

        existing = self._bridges.get(node_id)
        if existing and existing["proc"].poll() is None:
            return int(existing["port"])
        binary = self._resolve_binary()
        if not binary:
            raise RuntimeError(
                "xray core missing — click 下载内核 in the Plugins panel or set xray_path in settings"
            )
        port = self._free_port()
        config = self._build_config(node, port)
        cfg_path = self.ctx.plugin_dir / f"tunnel-{node_id[:12]}.json"
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        cfg_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
        proc = spawn_and_wait_port(binary, ["run", "-c", str(cfg_path)], port)
        self._bridges[node_id] = {"proc": proc, "port": port, "config": str(cfg_path)}
        self.ctx.log(f"bridge up on :{port} for {node.get('name')}")
        return port

    def stop_bridge(self, node_id: str) -> None:
        bridge = self._bridges.pop(node_id, None)
        if bridge:
            try:
                bridge["proc"].terminate()
            except Exception:
                pass

    def stop_all(self) -> None:
        for nid in list(self._bridges.keys()):
            self.stop_bridge(nid)

    def status(self, node_id: str) -> dict[str, Any] | None:
        bridge = self._bridges.get(node_id)
        if not bridge:
            return None
        return {"port": bridge["port"], "running": bridge["proc"].poll() is None}

    # ---- helpers ----
    def _free_port(self) -> int:
        import socket

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            return int(sock.getsockname()[1])

    def _build_config(self, node: dict[str, Any], local_port: int) -> dict[str, Any]:
        from backend.tunnel import build_xray_config

        return build_xray_config(node, local_port)
