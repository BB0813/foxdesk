"""Lightweight plugin system.

Plugins are directories containing a ``manifest.json`` and an entry module.
Built-in plugins ship in ``<app>/plugins/``; user plugins live in
``%APPDATA%/FoxDesk/plugins/``. Each manifest declares:

    {
      "id": "xray-bridge",
      "name": "Xray Bridge",
      "version": "1.0.0",
      "entry": "plugin.py:XrayBridgePlugin",
      "protocols": ["vless"],
      "description": "..."
    }

Extension points currently supported:
- ``protocols``: tunnel protocol handlers. A handler instance must expose
  ``ensure_bridge(node_id, node) -> local_port``, ``stop_bridge(node_id)``,
  ``stop_all()``, ``status(node_id)`` and may expose ``info()`` for UI state.
"""
from __future__ import annotations

import importlib.util
import json
import logging
import os
import subprocess
import socket
import time
from pathlib import Path
from typing import Any, Callable

log = logging.getLogger("foxdesk.plugins")


class PluginError(RuntimeError):
    pass


class PluginContext:
    """Services a plugin may use. Kept deliberately small."""

    def __init__(self, plugin_id: str, data_dir: Path, get_setting: Callable[[str, Any], Any]) -> None:
        self.plugin_id = plugin_id
        self.data_dir = Path(data_dir)
        self.plugin_dir = self.data_dir / "plugins" / plugin_id
        self._get_setting = get_setting

    def get_setting(self, key: str, default: Any = None) -> Any:
        return self._get_setting(key, default)

    def log(self, message: str) -> None:
        log.info("[%s] %s", self.plugin_id, message)


def _load_class(entry: str, base_dir: Path) -> Any:
    """entry format: '<file>:<ClassName>' relative to the manifest dir."""
    if ":" not in entry:
        raise PluginError(f"invalid entry (expected 'file.py:Class'): {entry}")
    file_name, class_name = entry.split(":", 1)
    module_path = base_dir / file_name
    if not module_path.is_file():
        raise PluginError(f"plugin entry file missing: {module_path}")
    spec = importlib.util.spec_from_file_location(f"foxdesk_plugin_{base_dir.name}_{class_name}", module_path)
    if spec is None or spec.loader is None:
        raise PluginError(f"cannot load plugin module: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    cls = getattr(module, class_name, None)
    if cls is None:
        raise PluginError(f"entry class missing: {class_name}")
    return cls


class LoadedPlugin:
    def __init__(self, manifest: dict[str, Any], instance: Any, base_dir: Path) -> None:
        self.manifest = manifest
        self.instance = instance
        self.base_dir = base_dir

    @property
    def id(self) -> str:
        return str(self.manifest.get("id") or self.base_dir.name)

    @property
    def name(self) -> str:
        return str(self.manifest.get("name") or self.id)

    @property
    def version(self) -> str:
        return str(self.manifest.get("version") or "0.0.0")

    @property
    def description(self) -> str:
        return str(self.manifest.get("description") or "")

    @property
    def protocols(self) -> list[str]:
        return [str(p).lower() for p in (self.manifest.get("protocols") or [])]


class PluginManager:
    def __init__(self, data_dir: Path, app_plugins_dir: Path, get_setting: Callable[[str, Any], Any]) -> None:
        self.data_dir = Path(data_dir)
        self.app_plugins_dir = Path(app_plugins_dir)
        self.user_plugins_dir = self.data_dir / "plugins"
        self._get_setting = get_setting
        self.plugins: dict[str, LoadedPlugin] = {}
        self.loaded = False

    def scan_and_load(self) -> None:
        if self.loaded:
            return
        for base in (self.app_plugins_dir, self.user_plugins_dir):
            if not base.is_dir():
                continue
            for child in sorted(base.iterdir()):
                manifest_path = child / "manifest.json"
                if not child.is_dir() or not manifest_path.is_file():
                    continue
                try:
                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                    pid = str(manifest.get("id") or child.name)
                    if pid in self.plugins:
                        # user plugins override built-ins with the same id
                        log.info("plugin %s overridden by user dir", pid)
                        continue
                    cls = _load_class(str(manifest.get("entry") or ""), child)
                    ctx = PluginContext(pid, self.data_dir, self._get_setting)
                    instance = cls(ctx)
                    self.plugins[pid] = LoadedPlugin(manifest, instance, child)
                    log.info("plugin loaded: %s %s", pid, manifest.get("version"))
                except Exception as exc:
                    log.warning("plugin load failed (%s): %s", child.name, exc)
        self.loaded = True

    def get_tunnel_handler(self, protocol: str) -> Any | None:
        """Return the plugin instance handling a tunnel protocol, or None."""
        self.scan_and_load()
        protocol = str(protocol or "").lower()
        for plugin in self.plugins.values():
            if protocol in plugin.protocols:
                return plugin.instance
        return None

    def list_plugins(self) -> list[dict[str, Any]]:
        self.scan_and_load()
        out = []
        for plugin in self.plugins.values():
            info: dict[str, Any] = {
                "id": plugin.id,
                "name": plugin.name,
                "version": plugin.version,
                "description": plugin.description,
                "protocols": plugin.protocols,
            }
            try:
                info["state"] = plugin.instance.info() if hasattr(plugin.instance, "info") else {}
            except Exception as exc:
                info["state"] = {"error": str(exc)}
            out.append(info)
        return out

    def shutdown_all(self) -> None:
        for plugin in self.plugins.values():
            try:
                if hasattr(plugin.instance, "shutdown"):
                    plugin.instance.shutdown()
            except Exception as exc:
                log.warning("plugin shutdown failed (%s): %s", plugin.id, exc)


def spawn_and_wait_port(binary: str, args: list[str], port: int, timeout: float = 8.0) -> subprocess.Popen:
    """Start a process and wait until the local port accepts connections.

    Shared helper for tunnel-bridge plugins. Raises RuntimeError on early
    exit or port timeout. The caller owns the Popen handle.
    """
    creationflags = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW
    proc = subprocess.Popen(
        [binary, *args],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
    )
    time.sleep(0.4)
    if proc.poll() is not None:
        raise RuntimeError(f"bridge process exited immediately (code {proc.returncode})")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return proc
        except OSError:
            time.sleep(0.15)
    try:
        proc.kill()
    except Exception:
        pass
    raise RuntimeError(f"bridge process did not open port {port}")
