"""D-B6: proxy exit-IP quality classification (residential vs datacenter).

Payment / AI-platform risk engines weight IP reputation heavily; a
datacenter exit IP is one of the most common hard-fail causes that
fingerprint work cannot compensate for. This module classifies the exit
IP reported by a successful proxy test into "residential" / "datacenter"
/ "mobile" / "unknown" using free, key-less, https-only IP info services.

Research aid only — classification is heuristic (ASN/org keywords) and
never a guarantee.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from urllib.request import Request, build_opener

# Known datacenter / hosting org markers (lowercase substring match).
# Deliberately biased towards false-negative ("residential") over
# false-positive: mislabeling a datacenter IP as residential hides a real
# risk; the reverse only costs an info-level hint.
_DATACENTER_KEYWORDS = (
    "amazon", "aws", "google cloud", "google llc", "microsoft", "azure",
    "digitalocean", "ovh", "hetzner", "linode", "vultr", "alibaba",
    "tencent", "huawei cloud", "oracle cloud", "cloudflare", "hosting",
    "host_", "datacamp", "m247", "leaseweb", "contabo", "choopa",
    "vandelay", "colocation", "colo", "server", "data center",
    "datacenter", "cdn", "cloud ", "cloudwab", "stark", "packethub",
    "psychz", "quadranet", "tzulo", "as-colo", "gcore", "aeza",
)

# Mobile-carrier markers → "mobile" quality (highest reputation tier).
_MOBILE_KEYWORDS = (
    "mobile", "wireless", "cellular", "t-mobile", "verizon wireless",
    "at&t mobility", "vodafone", "orange mobile", "china mobile",
    "china unicom mobile", "airtel", "jio", "kddi", "softbank",
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fetch_json(url: str, timeout: float = 8.0) -> dict[str, Any]:
    req = Request(url, headers={"User-Agent": "FoxDesk/proxy-quality"})
    with build_opener().open(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8", errors="replace"))
    return data if isinstance(data, dict) else {}


def classify_org(org: str) -> str:
    """Heuristic org/ISP classification from an ASN/org string."""
    text = (org or "").strip().lower()
    if not text:
        return "unknown"
    if any(k in text for k in _MOBILE_KEYWORDS):
        return "mobile"
    if any(k in text for k in _DATACENTER_KEYWORDS):
        return "datacenter"
    return "residential"


def _from_ipwho(ip: str, timeout: float) -> dict[str, Any] | None:
    try:
        data = _fetch_json(f"https://ipwho.is/{ip}", timeout=timeout)
    except Exception:
        return None
    if not data.get("success"):
        return None
    conn = data.get("connection") or {}
    org = str(conn.get("org") or conn.get("isp") or "")
    if not org:
        return None
    return {"org": org, "source": "ipwho.is"}


def _from_ipinfo(ip: str, timeout: float) -> dict[str, Any] | None:
    try:
        data = _fetch_json(f"https://ipinfo.io/{ip}/json", timeout=timeout)
    except Exception:
        return None
    org = str(data.get("org") or "")
    if not org:
        return None
    # ipinfo org format: "AS200651 FlokiNET"
    return {"org": org, "source": "ipinfo.io"}


def classify_exit_ip(ip: str, timeout: float = 8.0) -> dict[str, Any]:
    """Classify a proxy exit IP. Returns a quality record (no raises)."""
    result: dict[str, Any] = {
        "ip": ip,
        "quality": "unknown",
        "org": "",
        "source": None,
        "checked_at": _now_iso(),
        "note": "Heuristic ASN/org classification; not an IP-reputation guarantee.",
    }
    if not ip or ip == "unknown":
        return result
    for fetcher in (_from_ipwho, _from_ipinfo):
        info = fetcher(ip, timeout)
        if info is None:
            continue
        result["org"] = info["org"]
        result["source"] = info["source"]
        result["quality"] = classify_org(info["org"])
        return result
    return result
