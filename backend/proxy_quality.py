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


def is_valid_timezone(raw: str) -> bool:
    """True for an IANA timezone name resolvable on this host.

    When the host lacks the tz database (ZoneInfoNotFoundError), fall back to
    accepting well-formed IANA shapes instead of rejecting everything.
    """
    import re
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

    value = str(raw or "").strip()
    if not value:
        return False
    try:
        ZoneInfo(value)
        return True
    except ZoneInfoNotFoundError:
        return bool(re.fullmatch(r"[A-Za-z_]+/[A-Za-z0-9_+\-]+", value))
    except Exception:
        return False


def is_valid_ip(raw: str) -> bool:
    """True only for a literal IPv4/IPv6 address (no URL/path junk)."""
    import ipaddress

    try:
        ipaddress.ip_address(str(raw or "").strip())
        return True
    except Exception:
        return False


def classify_exit_ip(ip: str, timeout: float = 8.0) -> dict[str, Any]:
    """Classify a proxy exit IP. Returns a quality record (no raises)."""
    if not is_valid_ip(ip):
        ip = ""
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


# Rough country-code -> BCP-47 locale defaults for one-click environment
# matching (used by routes/proxies.py geo flow and routes/profiles.py
# timezone suggestion applier).
COUNTRY_LOCALES = {
    "US": "en-US", "GB": "en-GB", "CA": "en-CA", "AU": "en-AU", "NZ": "en-NZ",
    "DE": "de-DE", "AT": "de-AT", "CH": "de-CH", "FR": "fr-FR", "BE": "fr-BE",
    "ES": "es-ES", "MX": "es-MX", "AR": "es-AR", "IT": "it-IT", "NL": "nl-NL",
    "PT": "pt-PT", "BR": "pt-BR", "PL": "pl-PL", "CZ": "cs-CZ", "SK": "sk-SK",
    "HU": "hu-HU", "RO": "ro-RO", "BG": "bg-BG", "GR": "el-GR", "TR": "tr-TR",
    "RU": "ru-RU", "UA": "ru-UA", "SE": "sv-SE", "NO": "nb-NO", "DK": "da-DK",
    "FI": "fi-FI", "JP": "ja-JP", "KR": "ko-KR", "CN": "zh-CN", "TW": "zh-TW",
    "HK": "zh-HK", "SG": "zh-SG", "IN": "en-IN", "ID": "id-ID", "TH": "th-TH",
    "VN": "vi-VN", "PH": "en-PH", "MY": "ms-MY", "AE": "ar-AE", "SA": "ar-SA",
    "IL": "he-IL", "ZA": "en-ZA", "IE": "en-IE",
}


def locale_for_country(country_code: str) -> str:
    return COUNTRY_LOCALES.get(str(country_code or "").upper(), "en-US")
