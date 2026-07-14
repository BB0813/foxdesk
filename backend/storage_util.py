from __future__ import annotations

import base64
import json
import os
import secrets
import sys
from pathlib import Path
from typing import Any


def atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    """Write text atomically (tmp + replace) to reduce torn JSON on crash."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{secrets.token_hex(4)}.tmp")
    try:
        tmp.write_text(text, encoding=encoding)
        tmp.replace(path)
    finally:
        try:
            if tmp.exists():
                tmp.unlink(missing_ok=True)
        except OSError:
            pass


def atomic_write_json(path: Path, data: Any, *, indent: int = 2) -> None:
    atomic_write_text(path, json.dumps(data, ensure_ascii=False, indent=indent))


def _dpapi_protect(raw: bytes) -> bytes | None:
    if os.name != "nt":
        return None
    try:
        import ctypes
        import ctypes.wintypes

        class DATA_BLOB(ctypes.Structure):
            _fields_ = [("cbData", ctypes.wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32

        in_blob = DATA_BLOB(len(raw), ctypes.create_string_buffer(raw, len(raw)))
        out_blob = DATA_BLOB()
        if not crypt32.CryptProtectData(
            ctypes.byref(in_blob),
            "FoxDesk",
            None,
            None,
            None,
            0,
            ctypes.byref(out_blob),
        ):
            return None
        try:
            return ctypes.string_at(out_blob.pbData, out_blob.cbData)
        finally:
            kernel32.LocalFree(out_blob.pbData)
    except Exception:
        return None


def _dpapi_unprotect(raw: bytes) -> bytes | None:
    if os.name != "nt":
        return None
    try:
        import ctypes
        import ctypes.wintypes

        class DATA_BLOB(ctypes.Structure):
            _fields_ = [("cbData", ctypes.wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32

        in_blob = DATA_BLOB(len(raw), ctypes.create_string_buffer(raw, len(raw)))
        out_blob = DATA_BLOB()
        if not crypt32.CryptUnprotectData(
            ctypes.byref(in_blob),
            None,
            None,
            None,
            None,
            0,
            ctypes.byref(out_blob),
        ):
            return None
        try:
            return ctypes.string_at(out_blob.pbData, out_blob.cbData)
        finally:
            kernel32.LocalFree(out_blob.pbData)
    except Exception:
        return None


def _xor_obfuscate(raw: bytes, key: bytes) -> bytes:
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(raw))


def _fallback_key() -> bytes:
    # Machine-local obfuscation only (not a substitute for DPAPI on Windows).
    seed = f"{os.environ.get('COMPUTERNAME', '')}|{os.environ.get('USERNAME', '')}|FoxDeskSecret|v1"
    return seed.encode("utf-8")


SECRET_PREFIX_DPAPI = "enc:dpapi:"
SECRET_PREFIX_LOCAL = "enc:local:"


def protect_secret(value: str) -> str:
    """Encrypt/obfuscate a secret for at-rest storage. Empty stays empty."""
    if value is None:
        return ""
    text = str(value)
    if not text:
        return ""
    if text.startswith(SECRET_PREFIX_DPAPI) or text.startswith(SECRET_PREFIX_LOCAL):
        return text
    raw = text.encode("utf-8")
    sealed = _dpapi_protect(raw)
    if sealed is not None:
        return SECRET_PREFIX_DPAPI + base64.b64encode(sealed).decode("ascii")
    xored = _xor_obfuscate(raw, _fallback_key())
    return SECRET_PREFIX_LOCAL + base64.b64encode(xored).decode("ascii")


def unprotect_secret(value: str) -> str:
    """Decrypt a secret previously stored by protect_secret. Plaintext passes through."""
    if value is None:
        return ""
    text = str(value)
    if not text:
        return ""
    try:
        if text.startswith(SECRET_PREFIX_DPAPI):
            blob = base64.b64decode(text[len(SECRET_PREFIX_DPAPI) :])
            plain = _dpapi_unprotect(blob)
            if plain is None:
                return ""
            return plain.decode("utf-8", errors="replace")
        if text.startswith(SECRET_PREFIX_LOCAL):
            blob = base64.b64decode(text[len(SECRET_PREFIX_LOCAL) :])
            plain = _xor_obfuscate(blob, _fallback_key())
            return plain.decode("utf-8", errors="replace")
    except Exception:
        return ""
    return text


def is_protected_secret(value: str) -> bool:
    text = str(value or "")
    return text.startswith(SECRET_PREFIX_DPAPI) or text.startswith(SECRET_PREFIX_LOCAL)
