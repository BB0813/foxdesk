from __future__ import annotations

from pathlib import Path

import pytest

from backend.backup_crypto import (
    decrypt_blob,
    encrypt_blob,
    pack_files,
    read_encrypted_backup,
    unpack_files,
    write_encrypted_backup,
)


def test_encrypt_decrypt_roundtrip() -> None:
    from backend.backup_crypto import MAGIC_V2

    plain = b'{"hello":"world","n":1}'
    package = encrypt_blob("secret-pass", plain)
    assert package.startswith(MAGIC_V2)  # v2 AES-GCM is the default writer
    assert decrypt_blob("secret-pass", package) == plain
    with pytest.raises(ValueError):
        decrypt_blob("wrong-pass", package)


def test_pack_unpack_files() -> None:
    files = {"profiles.json": b'[{"id":"1"}]', "settings.json": b'{"a":1}'}
    blob = pack_files(files, meta={"app_version": "1.3.1"})
    meta, out = unpack_files(blob)
    assert meta["app_version"] == "1.3.1"
    assert out["profiles.json"] == files["profiles.json"]
    assert out["settings.json"] == files["settings.json"]


def test_write_read_encrypted_backup(tmp_path: Path) -> None:
    path = tmp_path / "foxdesk-backup-test.fdk"
    files = {"profiles.json": b"[]", "proxies.json": b"[]"}
    write_encrypted_backup(path, "abcd1234", files, {"note": "test"})
    meta, restored = read_encrypted_backup(path, "abcd1234")
    assert meta["note"] == "test"
    assert restored == files
    with pytest.raises(ValueError):
        read_encrypted_backup(path, "nope")


def test_v2_roundtrip_and_v1_compat(tmp_path: Path) -> None:
    """New backups are AES-GCM (v2); v1 HMAC-CTR packages still decrypt."""
    from backend.backup_crypto import MAGIC, MAGIC_V2, decrypt_blob, encrypt_blob

    pwd = "correct-horse-9"
    plain = pack_files({"profiles/a.json": b'{"x":1}'}, meta={"note": "v2"})
    blob = encrypt_blob(pwd, plain)
    assert blob.startswith(MAGIC_V2)
    assert decrypt_blob(pwd, blob) == plain

    # v1 (HMAC-CTR) hand-built package must remain readable.
    import hashlib
    import hmac as hmac_mod
    import secrets
    import struct
    import zlib

    from backend.backup_crypto import KEY_LEN, _derive_keys, _keystream

    salt = secrets.token_bytes(16)
    nonce = secrets.token_bytes(16)
    enc_key, mac_key = _derive_keys(pwd, salt)
    compressed = zlib.compress(plain, 9)
    stream = _keystream(enc_key, nonce, len(compressed))
    ct = bytes(a ^ b for a, b in zip(compressed, stream))
    mac = hmac_mod.new(mac_key, salt + nonce + ct, hashlib.sha256).digest()
    v1 = MAGIC + salt + nonce + struct.pack(">I", len(ct)) + ct + mac
    assert decrypt_blob(pwd, v1) == plain

    with pytest.raises(ValueError, match="wrong password or corrupted"):
        decrypt_blob(pwd, bytes(bytearray(blob[:-1] + bytes([blob[-1] ^ 1]))))


def test_short_password_rejected() -> None:
    from backend.backup_crypto import encrypt_blob

    with pytest.raises(ValueError, match="at least 8"):
        encrypt_blob("1234", b"x")
