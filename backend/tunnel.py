"""Tunnel node support: parse vless:// share links and bridge them to a
local SOCKS5 endpoint via an xray-core binary (user-provided).

Runtime logic modeled after proxy gateways like Resin: nodes are imported
as structured outbounds, a local core process exposes a SOCKS5 listener per
node, and the rest of the app treats that listener as an ordinary socks5
proxy.

No claims are made about bypass effectiveness; this only wires protocol
plumbing.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import time
import uuid as uuid_mod
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

XRAY_CONFIG_DIR_NAME = "tunnels"


class TunnelParseError(ValueError):
    pass


def parse_vless_uri(uri: str) -> dict[str, Any]:
    """Parse a vless:// share link into a structured node config.

    Format: vless://<uuid>@<host>:<port>?<params>#<name>
    Recognized params: encryption, security (tls|reality|none), sni, fp,
    pbk (reality publicKey), sid (reality shortId), flow, type (network:
    ws|tcp|grpc), host (ws host header), path (ws path), serviceName (grpc).
    """
    raw = str(uri or "").strip()
    if not raw.lower().startswith("vless://"):
        raise TunnelParseError("not a vless:// link")
    parsed = urlparse(raw)
    node_uuid = unquote(parsed.username or "")
    if not node_uuid:
        raise TunnelParseError("vless link is missing the user id")
    host = parsed.hostname or ""
    if not host:
        raise TunnelParseError("vless link is missing the server address")
    port = parsed.port or 443
    q = {k: v[0] for k, v in parse_qs(parsed.query).items() if v}
    name = unquote(parsed.fragment or "") or f"{host}:{port}"
    node: dict[str, Any] = {
        "protocol": "vless",
        "uuid": node_uuid,
        "address": host,
        "port": int(port),
        "encryption": q.get("encryption", "none"),
        "security": q.get("security", "none"),
        "sni": q.get("sni", ""),
        "fingerprint": q.get("fp", "chrome"),
        "flow": q.get("flow", ""),
        "network": q.get("type", "tcp"),
        "name": name,
    }
    if node["security"] == "reality":
        node["public_key"] = q.get("pbk", "")
        node["short_id"] = q.get("sid", "")
        if not node["public_key"]:
            raise TunnelParseError("reality node is missing pbk (public key)")
    if node["network"] == "ws":
        node["ws_host"] = q.get("host", "")
        node["ws_path"] = unquote(q.get("path", "/")) or "/"
    if node["network"] == "grpc":
        node["grpc_service"] = q.get("serviceName", "")
    return node


def node_display_name(node: dict[str, Any]) -> str:
    return str(node.get("name") or f"{node.get('address')}:{node.get('port')}")


def build_xray_config(node: dict[str, Any], local_port: int) -> dict[str, Any]:
    """Build an xray-core config exposing the node as a local SOCKS5 listener."""
    outbound: dict[str, Any] = {
        "protocol": "vless",
        "settings": {
            "vnext": [
                {
                    "address": node.get("address"),
                    "port": int(node.get("port") or 443),
                    "users": [
                        {
                            "id": node.get("uuid"),
                            "encryption": node.get("encryption") or "none",
                            **({"flow": node["flow"]} if node.get("flow") else {}),
                        }
                    ],
                }
            ]
        },
        "streamSettings": {
            "network": node.get("network") or "tcp",
            "security": node.get("security") or "none",
        },
    }
    security = node.get("security") or "none"
    stream = outbound["streamSettings"]
    if security == "tls":
        stream["tlsSettings"] = {
            "serverName": node.get("sni") or node.get("address"),
            "fingerprint": node.get("fingerprint") or "chrome",
        }
    elif security == "reality":
        stream["realitySettings"] = {
            "serverName": node.get("sni") or node.get("address"),
            "fingerprint": node.get("fingerprint") or "chrome",
            "publicKey": node.get("public_key", ""),
            "shortId": node.get("short_id", ""),
            "spiderX": "",
        }
    network = node.get("network") or "tcp"
    if network == "ws":
        ws: dict[str, Any] = {"path": node.get("ws_path") or "/"}
        if node.get("ws_host"):
            ws["headers"] = {"Host": node["ws_host"]}
        stream["wsSettings"] = ws
    elif network == "grpc":
        stream["grpcSettings"] = {"serviceName": node.get("grpc_service", "")}
    return {
        "log": {"loglevel": "warning"},
        "inbounds": [
            {
                "tag": "socks-in",
                "port": int(local_port),
                "listen": "127.0.0.1",
                "protocol": "socks",
                "settings": {"udp": True},
            }
        ],
        "outbounds": [outbound],
    }


def find_xray_binary(configured: str = "") -> str | None:
    """Locate an xray-core binary: configured path first, then PATH, then the
    FoxDesk data bin directory."""
    import os
    import shutil

    if configured and Path(configured).is_file():
        return configured
    found = shutil.which("xray") or shutil.which("xray.exe")
    if found:
        return found
    for home in (os.environ.get("APPDATA") or "", os.environ.get("XDG_DATA_HOME") or "", os.path.expanduser("~/.local/share")):
        if not home:
            continue
        for candidate in (
            Path(home) / "FoxDesk" / "bin" / "xray.exe",
            Path(home) / "FoxDesk" / "bin" / "xray",
        ):
            if candidate.is_file():
                return str(candidate)
    return None


def wait_for_port(port: int, timeout: float = 8.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.15)
    return False


class TunnelBridgeManager:
    """Spawns/stops one xray-core process per tunnel node, each exposing a
    local SOCKS5 listener. Handles are tracked per node id and cleaned up on
    stop_all (registered on app shutdown)."""

    def __init__(self, config_dir: Path, xray_path_provider: Any = None) -> None:
        self.config_dir = Path(config_dir)
        self.xray_path_provider = xray_path_provider  # optional () -> str
        self._bridges: dict[str, dict[str, Any]] = {}
        self.lock = __import__("threading").RLock()

    def _config_path(self, node_id: str) -> Path:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        return self.config_dir / f"tunnel-{node_id[:12]}.json"

    def start(self, node_id: str, node: dict[str, Any], xray_path: str = "") -> int:
        if not xray_path and self.xray_path_provider is not None:
            try:
                xray_path = str(self.xray_path_provider() or "")
            except Exception:
                xray_path = ""
        with self.lock:
            existing = self._bridges.get(node_id)
            if existing and existing["proc"].poll() is None:
                return int(existing["port"])
            from backend.tunnel import find_xray_binary

            resolved = find_xray_binary(xray_path)
            if not resolved:
                raise RuntimeError(
                    "xray core not found — set the xray path in settings or place xray.exe in %APPDATA%/FoxDesk/bin"
                )
            port = self._free_port()
            config = build_xray_config(node, port)
            cfg_path = self._config_path(node_id)
            cfg_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
            creationflags = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW
            proc = subprocess.Popen(
                [resolved, "run", "-c", str(cfg_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creationflags,
            )
            time.sleep(0.4)
            if proc.poll() is not None:
                raise RuntimeError(f"xray exited immediately (code {proc.returncode})")
            if not wait_for_port(port, timeout=8.0):
                try:
                    proc.kill()
                except Exception:
                    pass
                raise RuntimeError(f"xray bridge did not open port {port}")
            self._bridges[node_id] = {"proc": proc, "port": port, "config": str(cfg_path)}
            return port

    def stop(self, node_id: str) -> None:
        with self.lock:
            bridge = self._bridges.pop(node_id, None)
        if not bridge:
            return
        try:
            bridge["proc"].terminate()
        except Exception:
            pass

    def stop_all(self) -> None:
        with self.lock:
            bridges = list(self._bridges.items())
            self._bridges.clear()
        for _, bridge in bridges:
            try:
                bridge["proc"].terminate()
            except Exception:
                pass

    def status(self, node_id: str) -> dict[str, Any] | None:
        with self.lock:
            bridge = self._bridges.get(node_id)
        if not bridge:
            return None
        alive = bridge["proc"].poll() is None
        return {"port": bridge["port"], "running": alive}

    def _free_port(self) -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            return int(sock.getsockname()[1])

