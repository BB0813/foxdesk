from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import struct
import zlib
from pathlib import Path
from typing import Any


MAGIC = b"FOXDESK1"
KDF_ITERATIONS = 200_000
SALT_LEN = 16
NONCE_LEN = 16
MAC_LEN = 32
KEY_LEN = 32


def _derive_keys(password: str, salt: bytes) -> tuple[bytes, bytes]:
    """Derive enc + mac keys via PBKDF2-HMAC-SHA256."""
    material = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        KDF_ITERATIONS,
        dklen=KEY_LEN * 2,
    )
    return material[:KEY_LEN], material[KEY_LEN:]


def _keystream(enc_key: bytes, nonce: bytes, length: int) -> bytes:
    """HMAC-SHA256 counter mode keystream (stdlib-only AEAD building block)."""
    out = bytearray()
    counter = 0
    while len(out) < length:
        block = hmac.new(enc_key, nonce + struct.pack(">Q", counter), hashlib.sha256).digest()
        out.extend(block)
        counter += 1
    return bytes(out[:length])


def encrypt_blob(password: str, plaintext: bytes) -> bytes:
    """Password-based encrypt-then-MAC. Returns binary package."""
    if not password or len(password) < 4:
        raise ValueError("password must be at least 4 characters")
    salt = secrets.token_bytes(SALT_LEN)
    nonce = secrets.token_bytes(NONCE_LEN)
    enc_key, mac_key = _derive_keys(password, salt)
    compressed = zlib.compress(plaintext, level=9)
    stream = _keystream(enc_key, nonce, len(compressed))
    ciphertext = bytes(a ^ b for a, b in zip(compressed, stream))
    mac = hmac.new(mac_key, salt + nonce + ciphertext, hashlib.sha256).digest()
    # Binary layout: MAGIC | salt | nonce | u32 ct_len | ciphertext | mac
    return MAGIC + salt + nonce + struct.pack(">I", len(ciphertext)) + ciphertext + mac


def decrypt_blob(password: str, package: bytes) -> bytes:
    if not package.startswith(MAGIC):
        raise ValueError("not a FoxDesk encrypted backup")
    offset = len(MAGIC)
    salt = package[offset : offset + SALT_LEN]
    offset += SALT_LEN
    nonce = package[offset : offset + NONCE_LEN]
    offset += NONCE_LEN
    (ct_len,) = struct.unpack(">I", package[offset : offset + 4])
    offset += 4
    ciphertext = package[offset : offset + ct_len]
    offset += ct_len
    mac = package[offset : offset + MAC_LEN]
    if len(salt) != SALT_LEN or len(nonce) != NONCE_LEN or len(mac) != MAC_LEN:
        raise ValueError("corrupt backup package")
    if len(ciphertext) != ct_len:
        raise ValueError("truncated backup package")
    enc_key, mac_key = _derive_keys(password, salt)
    expect = hmac.new(mac_key, salt + nonce + ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(expect, mac):
        raise ValueError("wrong password or corrupted backup")
    stream = _keystream(enc_key, nonce, len(ciphertext))
    compressed = bytes(a ^ b for a, b in zip(ciphertext, stream))
    try:
        return zlib.decompress(compressed)
    except zlib.error as exc:
        raise ValueError("failed to decompress backup") from exc


def pack_files(files: dict[str, bytes], *, meta: dict[str, Any] | None = None) -> bytes:
    """Serialize a filename->bytes map to a JSON+base64 bundle (then encrypt outer)."""
    payload = {
        "meta": meta or {},
        "files": {name: base64.b64encode(data).decode("ascii") for name, data in files.items()},
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def unpack_files(blob: bytes) -> tuple[dict[str, Any], dict[str, bytes]]:
    data = json.loads(blob.decode("utf-8"))
    if not isinstance(data, dict) or "files" not in data:
        raise ValueError("invalid backup payload")
    files_raw = data.get("files") or {}
    if not isinstance(files_raw, dict):
        raise ValueError("invalid backup files map")
    files: dict[str, bytes] = {}
    for name, b64 in files_raw.items():
        files[str(name)] = base64.b64decode(str(b64))
    meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
    return meta, files


def write_encrypted_backup(path: Path, password: str, files: dict[str, bytes], meta: dict[str, Any]) -> None:
    plain = pack_files(files, meta=meta)
    package = encrypt_blob(password, plain)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(package)


def read_encrypted_backup(path: Path, password: str) -> tuple[dict[str, Any], dict[str, bytes]]:
    package = Path(path).read_bytes()
    # Support legacy zip backups (no MAGIC) by raising a typed error for callers.
    if not package.startswith(MAGIC):
        raise ValueError("legacy_or_plain_zip")
    plain = decrypt_blob(password, package)
    return unpack_files(plain)
