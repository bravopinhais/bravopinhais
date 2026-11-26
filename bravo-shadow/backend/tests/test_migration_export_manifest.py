from dataclasses import replace

import pytest

from app.core.migration_reconciliation import SourceSnapshotRecord
from app.core.migration_identity import SourceIdentity
from app.core.migration_source_snapshot import SourceSnapshot, calculate_snapshot_hash
from app.core.migration_export_manifest import (
    build_export_manifest,
    verify_export_manifest,
)


def source_snapshot(exported_at="2026-11-26T18:00:00-03:00"):
    records = (
        SourceSnapshotRecord(
            SourceIdentity("legacy-bravo", "moradores", "m-1"),
            "a" * 64,
        ),
    )
    return SourceSnapshot(
        source_system="legacy-bravo",
        source_baseline="baseline-2026-11-26",
        snapshot_hash=calculate_snapshot_hash("legacy-bravo", records),
        exported_at=exported_at,
        records=records,
    )


def manifest(**overrides):
    values = {
        "export_id": "export-2026-11-26-001",
        "schema_version": "1.0",
        "source_software": "legacy-app 4.2",
        "previous_manifest_hash": None,
    }
    values.update(overrides)
    return build_export_manifest(source_snapshot(), **values)


def test_export_manifest_is_immutable_and_contains_inventory_metadata_only():
    result = manifest()

    assert result.manifest_format_version == 1
    assert result.record_count == 1
    assert result.source_system == "legacy-bravo"
    assert len(result.snapshot_hash) == 64
    assert verify_export_manifest(result)
    assert not hasattr(result, "records")
    with pytest.raises((AttributeError, TypeError)):
        result.export_id = "changed"


def test_manifest_hash_is_deterministic_for_same_inputs():
    assert manifest() == manifest()


def test_manifest_hash_detects_tampering():
    result = manifest()
    tampered = object.__new__(type(result))
    for field in result.__dataclass_fields__:
        object.__setattr__(tampered, field, getattr(result, field))
    object.__setattr__(tampered, "export_id", "tampered")

    assert verify_export_manifest(result)
    assert not verify_export_manifest(tampered)


def test_manifest_can_link_to_previous_export_hash():
    previous = "b" * 64
    result = manifest(previous_manifest_hash=previous)

    assert result.previous_manifest_hash == previous
    assert verify_export_manifest(result)


@pytest.mark.parametrize("value", ["", "not-a-hash", "B" * 64])
def test_manifest_rejects_malformed_previous_hash(value):
    with pytest.raises(ValueError, match="previous_manifest_hash"):
        manifest(previous_manifest_hash=value)


@pytest.mark.parametrize("timestamp", ["", "2026-11-26T18:00:00", "not-a-date"])
def test_manifest_requires_timezone_aware_export_timestamp(timestamp):
    with pytest.raises(ValueError, match="exported_at"):
        build_export_manifest(
            source_snapshot(timestamp),
            export_id="export-001",
        )


def test_manifest_rejects_unsupported_format_and_invalid_record_count():
    result = manifest()

    with pytest.raises(ValueError):
        replace(result, manifest_format_version=2)
    with pytest.raises(ValueError):
        replace(result, record_count=-1)
