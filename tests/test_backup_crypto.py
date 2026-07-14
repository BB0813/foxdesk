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
    plain = b'{"hello":"world","n":1}'
    package = encrypt_blob("secret-pass", plain)
    assert package.startswith(b"FOXDESK1")
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
    write_encrypted_backup(path, "abcd", files, {"note": "test"})
    meta, restored = read_encrypted_backup(path, "abcd")
    assert meta["note"] == "test"
    assert restored == files
    with pytest.raises(ValueError):
        read_encrypted_backup(path, "nope")
