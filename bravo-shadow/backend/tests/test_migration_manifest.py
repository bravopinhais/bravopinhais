from dataclasses import FrozenInstanceError

import pytest

from app.core.migration_identity import ExistingSourceMapping, SourceIdentity
from app.core.migration_plan import DryRunCandidate
from app.core.migration_preflight import run_migration_preflight
from app.core.migration_report import build_preflight_report
from app.core.migration_manifest import (
    CANONICALIZATION_VERSION,
    build_migration_manifest,
    serialize_migration_manifest,
    verify_migration_manifest,
)


def envelope():
    return {
        "formatVersion": 1,
        "sourceSystem": "legacy-bravo",
        "sourceBranch": "upgrade/project-hardening",
        "sourceBaseline": "synthetic-manifest",
        "exportedAt": "2026-11-26T12:00:00-03:00",
        "collections": {
            "moradores": [{"id": "m-2"}, {"id": "m-1"}],
            "categorias": [{"id": "c-1"}],
        },
        "collectionPresence": {"moradores": True, "categorias": True},
        "snapshotHash": "d" * 64,
    }


def candidate(collection, legacy_id, *, mapping=None, collision=False):
    return DryRunCandidate(
        SourceIdentity("legacy-bravo", collection, legacy_id),
        "sha256:" + legacy_id,
        destination_id_exists=collision,
        existing_mapping=mapping,
    )


def build(envelope_value=None, candidates=None, **overrides):
    data = envelope_value or envelope()
    items = candidates if candidates is not None else (
        candidate("moradores", "m-2"),
        candidate(
            "moradores",
            "m-1",
            mapping=ExistingSourceMapping("sha256:m-1", "resident-1"),
        ),
        candidate("categorias", "c-1", collision=True),
    )
    result = run_migration_preflight(data, items)
    report = build_preflight_report(data, items, result)
    args = {
        "environment": "shadow-test",
        "importer_version": "1.2.0",
        "mapping_version": "1.0.0",
        "created_at": "2026-11-26T15:00:00-03:00",
    }
    args.update(overrides)
    return build_migration_manifest(data, items, result, report, **args)


def test_manifest_is_immutable_and_contains_identity_and_summary_only():
    manifest = build()

    assert manifest.format_version == 1
    assert manifest.canonicalization_version == CANONICALIZATION_VERSION
    assert manifest.batch_id.startswith("batch-")
    assert len(manifest.manifest_hash) == 64
    assert manifest.environment == "shadow-test"
    assert [record.legacy_id for record in manifest.records] == ["c-1", "m-1", "m-2"]
    assert dict(manifest.report_totals)["ready"] == 1
    assert dict(manifest.report_totals)["already_applied"] == 1
    assert dict(manifest.report_totals)["conflicts"] == 1
    with pytest.raises(FrozenInstanceError):
        manifest.environment = "production"


def test_manifest_hash_is_deterministic_for_same_inputs():
    first = build()
    second = build()

    assert first.batch_id == second.batch_id
    assert first.manifest_hash == second.manifest_hash
    assert first.records == second.records


def test_batch_identity_and_manifest_hash_change_when_importer_version_changes():
    first = build()
    second = build(importer_version="1.2.1")

    assert first.batch_id != second.batch_id
    assert first.manifest_hash != second.manifest_hash


def test_batch_identity_and_manifest_hash_change_when_mapping_version_changes():
    first = build()
    second = build(mapping_version="1.0.1")

    assert first.batch_id != second.batch_id
    assert first.manifest_hash != second.manifest_hash


def test_batch_identity_changes_when_snapshot_changes():
    first = build()
    changed = envelope()
    changed["snapshotHash"] = "e" * 64
    second = build(envelope_value=changed)

    assert first.batch_id != second.batch_id
    assert first.snapshot_hash != second.snapshot_hash


def test_manifest_refuses_invalid_preflight():
    data = envelope()
    data["formatVersion"] = 99
    items = (candidate("moradores", "m-1"),)
    result = run_migration_preflight(data, items)
    report = build_preflight_report(data, items, result)

    with pytest.raises(ValueError, match="pré-flight válido"):
        build_migration_manifest(
            data,
            items,
            result,
            report,
            environment="shadow-test",
            importer_version="1.0",
            mapping_version="1.0",
            created_at="2026-11-26T15:00:00-03:00",
        )


def test_manifest_hash_detects_tampering():
    from dataclasses import replace

    manifest = build()
    tampered = replace(manifest, environment="production")

    assert verify_migration_manifest(manifest) is True
    assert verify_migration_manifest(tampered) is False


def test_manifest_rejects_missing_version_or_environment():
    with pytest.raises(ValueError, match="environment"):
        build(environment=" ")
    with pytest.raises(ValueError, match="importer_version"):
        build(importer_version="")
