import hashlib
import json

import pytest

from app.core.migration_envelope_reader import read_envelope_bytes
from app.core.migration_pre_import_manifest import build_pre_import_manifest
from app.core.migration_source_integrity import build_source_integrity_report


def _source():
    envelope = {
        "formatVersion": 1,
        "sourceSystem": "legacy-synthetic",
        "sourceBranch": "fixture",
        "sourceBaseline": "baseline-01",
        "exportedAt": "2026-11-27T10:00:00-03:00",
        "collections": {
            "categorias": [{"id": "cat-01", "nome": "Geral"}],
            "moradores": [{"id": "mor-01", "bloco": "A", "apartamento": "01", "nome": "DADO PRIVADO"}],
        },
        "collectionPresence": {"categorias": True, "moradores": True},
        "snapshotHash": "a" * 64,
    }
    raw = json.dumps(envelope, ensure_ascii=False).encode("utf-8")
    return read_envelope_bytes(raw), envelope


def _manifest(source, integrity, **overrides):
    args = {
        "contract_version": "contracts-v1",
        "compatibility_mapping_version": "compat-map-v1",
        "special_mapping_version": "special-map-v1",
        "importer_version": "not-implemented-v1",
        "target_schema_version": "shadow-schema-v1",
        **overrides,
    }
    return build_pre_import_manifest(source, integrity, **args)


def test_manifest_binds_raw_file_hash_separately_from_snapshot_hash():
    source, _ = _source()
    integrity = build_source_integrity_report(source.envelope["collections"])
    manifest = _manifest(source, integrity)

    assert manifest.raw_source_sha256 == hashlib.sha256(
        json.dumps({
            "formatVersion": 1,
            "sourceSystem": "legacy-synthetic",
            "sourceBranch": "fixture",
            "sourceBaseline": "baseline-01",
            "exportedAt": "2026-11-27T10:00:00-03:00",
            "collections": {
                "categorias": [{"id": "cat-01", "nome": "Geral"}],
                "moradores": [{"id": "mor-01", "bloco": "A", "apartamento": "01", "nome": "DADO PRIVADO"}],
            },
            "collectionPresence": {"categorias": True, "moradores": True},
            "snapshotHash": "a" * 64,
        }, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    assert manifest.snapshot_hash == "a" * 64
    assert manifest.raw_source_sha256 != manifest.snapshot_hash


def test_manifest_is_deterministic_and_mapping_order_independent():
    source, _ = _source()
    integrity = build_source_integrity_report(source.envelope["collections"])
    first = _manifest(
        source, integrity, compatibility_mapping={"z": "target-z", "a": "target-a"}
    )
    second = _manifest(
        source, integrity, compatibility_mapping={"a": "target-a", "z": "target-z"}
    )
    assert first.canonical_json == second.canonical_json
    assert first.manifest_sha256 == second.manifest_sha256
    assert first.manifest_sha256 == hashlib.sha256(first.canonical_json.encode()).hexdigest()


def test_manifest_stays_blocked_and_never_authorizes_writes_by_default():
    source, _ = _source()
    integrity = build_source_integrity_report(source.envelope["collections"])
    manifest = _manifest(source, integrity)

    assert manifest.readiness == "blocked"
    assert "condominio_singleton_locator_unconfirmed" in manifest.pending_gates
    assert manifest.human_approval_required is True
    assert manifest.writes_authorized is False


def test_manifest_contains_no_record_values_or_personal_data():
    source, _ = _source()
    integrity = build_source_integrity_report(source.envelope["collections"])
    manifest = _manifest(source, integrity)

    assert "DADO PRIVADO" not in manifest.canonical_json
    assert "mor-01" not in manifest.canonical_json
    assert "cat-01" not in manifest.canonical_json


def test_manifest_can_only_become_awaiting_approval_after_all_gates_clear():
    source, _ = _source()
    integrity = build_source_integrity_report(source.envelope["collections"])
    # The current integrity report is intentionally review_required.
    manifest = _manifest(source, integrity, pending_gates=())
    assert manifest.readiness == "blocked"


def test_manifest_rejects_missing_version_and_invalid_gate():
    source, _ = _source()
    integrity = build_source_integrity_report(source.envelope["collections"])
    with pytest.raises(ValueError, match="contract_version"):
        _manifest(source, integrity, contract_version=" ")
    with pytest.raises(ValueError, match="pending_gates"):
        _manifest(source, integrity, pending_gates=("ok", " "))
