"""Proxy pool routes: CRUD, import, assignment, testing, health."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from backend.core import Profile, activity, now_iso, proxy_pool, store
from backend.models import (
    ProxyAssignRequest,
    ProxyPoolImportRequest,
    ProxyPoolIn,
    ProxyTestRequest,
)
from backend.proxy_test import _test_proxy_connection
from backend.wiring import proxy_health

router = APIRouter()


@router.get("/api/proxies")
def list_proxies() -> list[dict[str, Any]]:
    return proxy_pool.all()


@router.post("/api/proxies")
def create_proxy(item: ProxyPoolIn) -> dict[str, Any]:
    try:
        created = proxy_pool.create(item.model_dump())
        activity.log("proxy_create", created.get("name") or created.get("server") or "")
        return created
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


@router.put("/api/proxies/{proxy_id}")
def update_proxy(proxy_id: str, item: ProxyPoolIn) -> dict[str, Any]:
    try:
        return proxy_pool.update(proxy_id, item.model_dump())
    except KeyError:
        raise HTTPException(status_code=404, detail="proxy not found") from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


@router.delete("/api/proxies/{proxy_id}")
def delete_proxy(proxy_id: str) -> dict[str, bool]:
    try:
        proxy_pool.delete(proxy_id)
        activity.log("proxy_delete", proxy_id)
        return {"ok": True}
    except KeyError:
        raise HTTPException(status_code=404, detail="proxy not found") from None


@router.post("/api/proxies/import")
def import_proxy_pool(request: ProxyPoolImportRequest) -> dict[str, Any]:
    imported = proxy_pool.import_lines(request.lines, replace=request.replace)
    activity.log("proxy_import", f"count={len(imported)}")
    return {"ok": True, "count": len(imported), "proxies": imported}


@router.post("/api/proxies/{proxy_id}/test")
def test_proxy_pool_item(proxy_id: str) -> dict[str, Any]:
    try:
        item = proxy_pool.get(proxy_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="proxy not found") from None
    result = _test_proxy_connection(item.get("server") or "", item.get("username") or "", item.get("password") or "")
    try:
        proxy_pool.mark_test_result(proxy_id, result)
    except KeyError:
        pass
    return result


@router.post("/api/proxies/{proxy_id}/quality-check")
def quality_check_proxy(proxy_id: str) -> dict[str, Any]:
    """D-B6: run a proxy test, then classify the exit IP (residential vs
    datacenter) and store the quality record on the pool item."""
    from backend.proxy_quality import classify_exit_ip

    try:
        item = proxy_pool.get(proxy_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="proxy not found") from None
    result = _test_proxy_connection(item.get("server") or "", item.get("username") or "", item.get("password") or "")
    try:
        proxy_pool.mark_test_result(proxy_id, result)
    except KeyError:
        pass
    quality = classify_exit_ip(str(result.get("exit_ip") or ""))
    if result.get("ok"):
        try:
            proxy_pool.mark_quality(proxy_id, quality)
        except KeyError:
            pass
    activity.log(
        "proxy_quality_check",
        f"{proxy_id} quality={quality.get('quality')} org={quality.get('org')[:60]}",
    )
    return {"ok": bool(result.get("ok")), "test": result, "quality": quality}


@router.post("/api/proxies/assign")
def assign_proxy_to_profiles(request: ProxyAssignRequest) -> dict[str, Any]:
    if request.proxy_id:
        try:
            proxy_pool.get(request.proxy_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="proxy not found") from None
    profiles = store.all()
    updated = 0
    for idx, profile in enumerate(profiles):
        if profile.id not in request.profile_ids:
            continue
        dump = profile.model_dump()
        dump["proxy_id"] = request.proxy_id
        if request.proxy_id:
            item = proxy_pool.get(request.proxy_id)
            dump["proxy"] = {
                "server": item.get("server") or "",
                "username": item.get("username") or "",
                "password": item.get("password") or "",
            }
        dump["updated_at"] = now_iso()
        profiles[idx] = Profile(**dump)
        updated += 1
    store.save_all(profiles)
    activity.log("proxy_assign", f"updated={updated}")
    return {"ok": True, "updated": updated}


@router.post("/api/proxy/test")
def proxy_test(request: ProxyTestRequest) -> dict[str, Any]:
    server = request.server.strip()
    if not server:
        raise HTTPException(status_code=400, detail="proxy server is required")
    if "://" not in server:
        server = f"http://{server}"
    return _test_proxy_connection(server, request.username, request.password)


# --- Exit-IP geo + one-click environment matching (⑤⑥) ---
_GEO_HOST = "ipwho.is"

# Rough country-code → BCP-47 locale defaults for the env matcher.
_COUNTRY_LOCALES = {
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


def _fetch_geo_via_proxy(proxy_url: str, username: str = "", password: str = "", timeout: float = 10.0) -> dict[str, Any]:
    """Fetch exit-IP geo (ipwho.is over https) through the proxy itself.

    Same trust level as the proxy test — the query goes through the user's
    own proxy, over TLS. Quality classification reuses proxy_quality.
    """
    import json
    import time as _time
    from urllib.parse import quote, urlparse
    from urllib.request import ProxyHandler, Request, build_opener

    from backend.proxy_quality import classify_org
    from backend.proxy_test import _socks4_connect, _socks5_connect, _tls_wrap

    parsed = urlparse(proxy_url)
    scheme = parsed.scheme.lower()
    host = parsed.hostname or ""
    port = parsed.port or (1080 if "socks" in scheme else 8080)
    user = username or (parsed.username or "")
    pwd = password if password is not None else (parsed.password or "")

    start = _time.monotonic()
    data: dict[str, Any] = {}
    try:
        if scheme in ("http", "https"):
            auth = f"{quote(user, safe='')}:{quote(pwd or '', safe='')}@" if user else ""
            proxy_handler = ProxyHandler(
                {"http": f"http://{auth}{host}:{port}", "https": f"http://{auth}{host}:{port}"}
            )
            opener = build_opener(proxy_handler)
            resp = opener.open(Request(f"https://{_GEO_HOST}/"), timeout=timeout)
            data = json.loads(resp.read())
        elif scheme in ("socks5", "socks4"):
            if scheme == "socks5":
                sock = _socks5_connect(host, port, _GEO_HOST, 443, timeout=timeout, username=user, password=pwd or "")
            else:
                sock = _socks4_connect(host, port, _GEO_HOST, 443, timeout=timeout)
            sock = _tls_wrap(sock, _GEO_HOST)
            sock.sendall(f"GET / HTTP/1.1\r\nHost: {_GEO_HOST}\r\nConnection: close\r\n\r\n".encode())
            response = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk
            sock.close()
            body = response.split(b"\r\n\r\n", 1)[-1] if b"\r\n\r\n" in response else b"{}"
            data = json.loads(body)
        else:
            return {"ok": False, "error": f"Unsupported proxy scheme: {scheme}"}

        latency = int((_time.monotonic() - start) * 1000)
        if not data.get("success", True):
            return {"ok": False, "error": str(data.get("message") or "geo lookup failed"), "latency_ms": latency}
        tz_block = data.get("timezone") or {}
        conn = data.get("connection") or {}
        org = str(conn.get("org") or conn.get("isp") or "")
        return {
            "ok": True,
            "exit_ip": data.get("ip"),
            "country": data.get("country"),
            "country_code": data.get("country_code"),
            "timezone": tz_block.get("id"),
            "utc_offset": tz_block.get("utc"),
            "org": org,
            "asn": conn.get("asn"),
            "connection_type": classify_org(org),
            "latency_ms": latency,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc), "latency_ms": int((_time.monotonic() - start) * 1000)}


def _persist_proxy_geo(proxy_url: str, geo: dict[str, Any]) -> None:
    """Remember last geo on the matching pool item so environment_risks can
    compare profile.timezone against the proxy's actual region."""
    if not geo.get("ok"):
        return
    tail = proxy_url.split("//")[-1]
    for item in proxy_pool.all():
        server = item.get("server") or ""
        if server and (server in proxy_url or tail.endswith(server.split("//")[-1])):
            try:
                proxy_pool.update(item["id"], {"last_geo": geo})
            except Exception:
                pass
            return


@router.post("/api/proxy/geo")
def proxy_geo(request: ProxyTestRequest) -> dict[str, Any]:
    server = request.server.strip()
    if not server:
        raise HTTPException(status_code=400, detail="proxy server is required")
    if "://" not in server:
        server = f"http://{server}"
    geo = _fetch_geo_via_proxy(server, request.username, request.password)
    if geo.get("ok") and geo.get("country_code"):
        geo["suggested_locale"] = _COUNTRY_LOCALES.get(str(geo["country_code"]).upper(), "en-US")
    _persist_proxy_geo(server, geo)
    return geo


@router.post("/api/proxies/health-check")
def proxies_health_check_now() -> dict[str, Any]:
    result = proxy_health.run_once()
    activity.log("proxy_health_check", f"checked={result.get('checked')} failed={result.get('failed')}")
    return result


@router.get("/api/proxies/health-status")
def proxies_health_status() -> dict[str, Any]:
    return {"ok": True, **proxy_health.status()}
