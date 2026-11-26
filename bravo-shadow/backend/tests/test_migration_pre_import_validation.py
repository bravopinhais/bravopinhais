import pytest

from app.core.migration_export_manifest import build_export_manifest
from app.core.migration_identity import SourceIdentity
from app.core.migration_pre_import_validation import validate_pre_import_evidence
from app.core.migration_reconciliation import (
    ReconciliationReport,
    SourceSnapshotRecord,
)
from app.core.migration_source_snapshot import SourceSnapshot, calculate_snapshot_hash


def evidence():
    records = (
        SourceSnapshotRecord(
            SourceIdentity("legacy-bravo", "moradores", "m-1"),
            "a" * 64,
        ),
    )
    snapshot = SourceSnapshot(
        source_system="legacy-bravo",
        source_baseline="baseline-1",
        snapshot_hash=calculate_snapshot_hash("legacy-bravo", records),
        exported_at="2026-11-26T18:00:00-03:00",
        records=records,
    )
    manifest = build_export_manifest(snapshot, export_id="export-001")
    reconciliation = ReconciliationReport(
        valid=True,
        matched=1,
        missing_mapping=0,
        changed_source_hash=0,
        orphaned_mapping=0,
        duplicate_source_mapping=0,
        duplicate_destination=0,
        issues=(),
    )
    return snapshot, manifest, reconciliation


def validate(snapshot, manifest, reconciliation, chain=None):
    return validate_pre_import_evidence(
        snapshot=snapshot,
        manifest=manifest,
        export_chain=chain if chain is not None else (manifest,),
        reconciliation=reconciliation,
    )


def test_all_consistent_evidence_is_ready_for_separate_approval():
    snapshot, manifest, reconciliation = evidence()

    result = validate(snapshot, manifest, reconciliation)

    assert result.ready
    assert result.blockers == ()
    assert result.snapshot_records == 1
    assert result.reconciliation_matched == 1


def test_manifest_must_match_snapshot_inventory():
    snapshot, manifest, reconciliation = evidence()
    tampered = object.__new__(type(manifest))
    for field in manifest.__dataclass_fields__:
        object.__setattr__(tampered, field, getattr(manifest, field))
    object.__setattr__(tampered, "record_count", 9)

    result = validate(snapshot, tampered, reconciliation)

    assert not result.ready
    assert "manifest_hash_invalid" in result.blockers
    assert "record_count_mismatch" in result.blockers


def test_broken_export_chain_blocks_readiness():
    snapshot, manifest, reconciliation = evidence()
    first = build_export_manifest(snapshot, export_id="export-000")
    broken = build_export_manifest(
        snapshot,
        export_id="export-001",
        previous_manifest_hash="b" * 64,
    )

    result = validate(snapshot, broken, reconciliation, (first, broken))

    assert not result.ready
    assert "export_chain:previous_hash_mismatch:1" in result.blockers


def test_manifest_must_be_chain_tip():
    snapshot, manifest, reconciliation = evidence()
    later = build_export_manifest(
        snapshot,
        export_id="export-002",
        previous_manifest_hash=manifest.manifest_hash,
    )

    result = validate(snapshot, manifest, reconciliation, (manifest, later))

    assert not result.ready
    assert "manifest_not_chain_tip" in result.blockers


def test_reconciliation_conflict_blocks_readiness():
    snapshot, manifest, _ = evidence()
    conflict = ReconciliationReport(
        valid=False,
        matched=0,
        missing_mapping=1,
        changed_source_hash=0,
        orphaned_mapping=0,
        duplicate_source_mapping=0,
        duplicate_destination=0,
        issues=("missing_mapping",),
    )

    result = validate(snapshot, manifest, conflict)

    assert not result.ready
    assert "reconciliation:missing_mapping" in result.blockers


def test_input_contract_rejects_mutable_chain():
    snapshot, manifest, reconciliation = evidence()

    with pytest.raises(TypeError, match="tupla"):
        validate_pre_import_evidence(
            snapshot=snapshot,
            manifest=manifest,
            export_chain=[manifest],
            reconciliation=reconciliation,
        )
