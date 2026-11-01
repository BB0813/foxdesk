"""Bridge manager accessor. The singleton lives in wiring.py (built with
settings-driven xray resolution); this module exists so low-level modules can
import it without cycles."""
from __future__ import annotations


def get_bridge_manager():
    from backend.wiring import bridge_manager

    return bridge_manager


def stop_all_bridges() -> None:
    from backend.wiring import bridge_manager

    bridge_manager.stop_all()
