"""Proxy connectivity testing (HTTP/HTTPS/SOCKS4/SOCKS5) — stdlib only."""
from __future__ import annotations

import json
import socket
from typing import Any


def _socks5_connect(
    proxy_host: str,
    proxy_port: int,
    target_host: str,
    target_port: int,
    timeout: float = 10.0,
    username: str = "",
    password: str = "",
) -> socket.socket:
    """Raw SOCKS5 CONNECT handshake with optional username/password auth."""
    import socket as _sock

    sock = _sock.create_connection((proxy_host, proxy_port), timeout=timeout)
    if username:
        # Offer user/pass auth
        sock.sendall(b"\x05\x02\x00\x02")
    else:
        sock.sendall(b"\x05\x01\x00")
    resp = sock.recv(2)
    if len(resp) < 2 or resp[0] != 0x05:
        sock.close()
        raise ConnectionError("SOCKS5 proxy greeting failed")
    method = resp[1]
    if method == 0x02:
        u = username.encode("utf-8")[:255]
        p = password.encode("utf-8")[:255]
        sock.sendall(b"\x01" + bytes([len(u)]) + u + bytes([len(p)]) + p)
        auth_resp = sock.recv(2)
        if len(auth_resp) < 2 or auth_resp[1] != 0x00:
            sock.close()
            raise ConnectionError("SOCKS5 username/password authentication failed")
    elif method != 0x00:
        sock.close()
        raise ConnectionError(f"SOCKS5 proxy auth negotiation failed (method={method})")
    # CONNECT request
    addr = target_host.encode("ascii")
    req = b"\x05\x01\x00\x03" + bytes([len(addr)]) + addr + target_port.to_bytes(2, "big")
    sock.sendall(req)
    resp = sock.recv(4)
    if len(resp) < 4 or resp[1] != 0x00:
        sock.close()
        raise ConnectionError(f"SOCKS5 CONNECT failed: error code {resp[1] if len(resp) > 1 else 'unknown'}")
    # Drain bind addr
    atyp = resp[3] if len(resp) > 3 else 1
    if atyp == 1:
        sock.recv(4 + 2)
    elif atyp == 3:
        ln = sock.recv(1)
        if ln:
            sock.recv(ln[0] + 2)
    elif atyp == 4:
        sock.recv(16 + 2)
    return sock


def _socks4_connect(proxy_host: str, proxy_port: int, target_host: str, target_port: int, timeout: float = 10.0) -> socket.socket:
    """Raw SOCKS4 CONNECT handshake."""
    import socket as _sock
    import struct
    sock = _sock.create_connection((proxy_host, proxy_port), timeout=timeout)
    ip_parts = target_host.split(".")
    if len(ip_parts) == 4:
        ip_bytes = bytes(int(p) for p in ip_parts)
    else:
        raise ConnectionError("SOCKS4 requires IPv4 target for CONNECT")
    req = b"\x04\x01" + struct.pack("!H", target_port) + ip_bytes + b"\x00"
    sock.sendall(req)
    resp = sock.recv(8)
    if len(resp) < 2 or resp[1] != 0x5A:
        sock.close()
        raise ConnectionError(f"SOCKS4 CONNECT failed: code {resp[1] if len(resp) > 1 else 'unknown'}")
    return sock


def _tls_wrap(sock: Any, server_hostname: str) -> Any:
    import ssl

    ctx = ssl.create_default_context()
    return ctx.wrap_socket(sock, server_hostname=server_hostname)


def _test_proxy_connection(proxy_url: str, username: str = "", password: str = "", timeout: float = 10.0) -> dict[str, Any]:
    """Test proxy by connecting through it to an IP-check endpoint."""
    import time as _time
    from urllib.parse import quote, urlparse
    from urllib.request import ProxyHandler, Request, build_opener

    parsed = urlparse(proxy_url)
    scheme = parsed.scheme.lower()
    host = parsed.hostname or ""
    port = parsed.port or (1080 if "socks" in scheme else 8080)
    user = username or (parsed.username or "")
    pwd = password if password is not None else (parsed.password or "")

    start = _time.monotonic()
    # IP-check endpoint must be https — plaintext leak would expose the exit
    # IP (and this machine's traffic) to anyone on the path.
    check_host = "api.ipify.org"
    check_url = "https://api.ipify.org?format=json"
    try:
        if scheme in ("http", "https"):
            if user:
                auth = f"{quote(user, safe='')}:{quote(pwd or '', safe='')}@"
            else:
                auth = ""
            proxy_with_auth = f"{scheme}://{auth}{host}:{port}"
            proxy_handler = ProxyHandler({"http": proxy_with_auth, "https": proxy_with_auth})
            opener = build_opener(proxy_handler)
            req = Request(check_url)
            resp = opener.open(req, timeout=timeout)
            data = json.loads(resp.read())
            ip = data.get("ip", "unknown")
        elif scheme == "socks5":
            sock = _socks5_connect(host, port, check_host, 443, timeout=timeout, username=user, password=pwd or "")
            sock = _tls_wrap(sock, check_host)
            sock.sendall(b"GET /?format=json HTTP/1.1\r\nHost: api.ipify.org\r\nConnection: close\r\n\r\n")
            response = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk
            sock.close()
            body = response.split(b"\r\n\r\n", 1)[-1] if b"\r\n\r\n" in response else b"{}"
            data = json.loads(body)
            ip = data.get("ip", "unknown")
        elif scheme == "socks4":
            sock = _socks4_connect(host, port, check_host, 443, timeout=timeout)
            sock = _tls_wrap(sock, check_host)
            sock.sendall(b"GET /?format=json HTTP/1.1\r\nHost: api.ipify.org\r\nConnection: close\r\n\r\n")
            response = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk
            sock.close()
            body = response.split(b"\r\n\r\n", 1)[-1] if b"\r\n\r\n" in response else b"{}"
            data = json.loads(body)
            ip = data.get("origin", "unknown")
        else:
            return {"ok": False, "error": f"Unsupported proxy scheme: {scheme}", "latency_ms": None, "exit_ip": None}

        latency = int((_time.monotonic() - start) * 1000)
        return {"ok": True, "exit_ip": ip, "latency_ms": latency, "scheme": scheme}
    except Exception as exc:
        latency = int((_time.monotonic() - start) * 1000)
        return {"ok": False, "error": str(exc), "latency_ms": latency, "exit_ip": None, "scheme": scheme}


def test_proxy_item_for_health(item: dict[str, Any]) -> dict[str, Any]:
    return _test_proxy_connection(
        item.get("server") or "",
        item.get("username") or "",
        item.get("password") or "",
    )
