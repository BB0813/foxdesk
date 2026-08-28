"""profiles.json schema versioning: legacy bare-list files stay readable and
are upgraded to the v2 wrapped document on the next write."""

from __future__ import annotations

import json

import pytest

from backend.core import PROFILE_SCHEMA_VERSION, ProfileStore


class TestProfileSchemaVersioning:
    def test_seed_writes_v2_document(self, tmp_path):
        path = tmp_path / "profiles.json"
        ProfileStore(path)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["schema_version"] == PROFILE_SCHEMA_VERSION == 2
        assert isinstance(data["profiles"], list)
        assert len(data["profiles"]) == 1

    def test_reads_legacy_bare_list(self, tmp_path):
        path = tmp_path / "profiles.json"
        legacy = [
            {
                "id": "legacy-1",
                "name": "Legacy Profile",
                "created_at": "2026-01-01T00:00:00+00:00",
                "updated_at": "2026-01-01T00:00:00+00:00",
            }
        ]
        path.write_text(json.dumps(legacy), encoding="utf-8")
        store = ProfileStore(path)
        profiles = store.all()
        assert [p.name for p in profiles] == ["Legacy Profile"]

    def test_save_upgrades_legacy_to_v2(self, tmp_path):
        path = tmp_path / "profiles.json"
        legacy = [
            {
                "id": "legacy-1",
                "name": "Legacy Profile",
                "created_at": "2026-01-01T00:00:00+00:00",
                "updated_at": "2026-01-01T00:00:00+00:00",
            }
        ]
        path.write_text(json.dumps(legacy), encoding="utf-8")
        store = ProfileStore(path)
        store.save_all(store.all())
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["schema_version"] == 2
        assert [p["name"] for p in data["profiles"]] == ["Legacy Profile"]

    def test_create_clone_update_roundtrip(self, tmp_path):
        from backend.models import ProfileIn

        path = tmp_path / "profiles.json"
        store = ProfileStore(path)
        created = store.create(ProfileIn(name="Roundtrip"))
        assert created.id
        cloned = store.clone(created.id)
        assert cloned.name == "Roundtrip Copy"
        updated = store.update(created.id, ProfileIn(name="Roundtrip v2"))
        assert updated.name == "Roundtrip v2"
        store.delete(created.id)
        remaining = store.all()
        # seed + clone remain
        assert cloned.id in [p.id for p in remaining]
        assert created.id not in [p.id for p in remaining]
        assert len(remaining) == 2
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["schema_version"] == 2
