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


@router.post("/api/proxies/health-check")
def proxies_health_check_now() -> dict[str, Any]:
    result = proxy_health.run_once()
    activity.log("proxy_health_check", f"checked={result.get('checked')} failed={result.get('failed')}")
    return result


@router.get("/api/proxies/health-status")
def proxies_health_status() -> dict[str, Any]:
    return {"ok": True, **proxy_health.status()}
