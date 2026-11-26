from app.core.migration_export_chain import verify_export_chain
from app.core.migration_export_manifest import build_export_manifest
from app.core.migration_reconciliation import SourceSnapshotRecord
from app.core.migration_identity import SourceIdentity
from app.core.migration_source_snapshot import SourceSnapshot, calculate_snapshot_hash


def snapshot():
    records = (
        SourceSnapshotRecord(SourceIdentity("legacy-bravo", "moradores", "m-1"), "a" * 64),
    )
    return SourceSnapshot(
        source_system="legacy-bravo",
        source_baseline="baseline-1",
        snapshot_hash=calculate_snapshot_hash("legacy-bravo", records),
        exported_at="2026-11-26T18:00:00-03:00",
        records=records,
    )


def make_manifest(export_id, previous=None):
    return build_export_manifest(
        snapshot(),
        export_id=export_id,
        previous_manifest_hash=previous,
    )


def test_verifies_single_unlinked_initial_manifest():
    first = make_manifest("export-001")

    result = verify_export_chain((first,))

    assert result.valid
    assert result.checked == 1
    assert result.issues == ()


def test_verifies_linked_manifests_in_order():
    first = make_manifest("export-001")
    second = make_manifest("export-002", first.manifest_hash)

    result = verify_export_chain((first, second))

    assert result.valid
    assert result.checked == 2


def test_rejects_broken_link():
    first = make_manifest("export-001")
    second = make_manifest("export-002", "b" * 64)

    result = verify_export_chain((first, second))

    assert not result.valid
    assert "previous_hash_mismatch:1" in result.issues


def test_rejects_reordered_chain():
    first = make_manifest("export-001")
    second = make_manifest("export-002", first.manifest_hash)

    result = verify_export_chain((second, first))

    assert not result.valid


def test_can_anchor_first_manifest_to_independently_retained_hash():
    prior = "c" * 64
    first = make_manifest("export-002", prior)

    assert verify_export_chain(
        (first,),
        expected_previous_manifest_hash=prior,
    ).valid


def test_rejects_duplicate_export_ids():
    first = make_manifest("export-001")
    second = make_manifest("export-001", first.manifest_hash)

    result = verify_export_chain((first, second))

    assert not result.valid
    assert "duplicate_export_id:1" in result.issues


def test_detects_manifest_field_tampering():
    first = make_manifest("export-001")
    tampered = object.__new__(type(first))
    for field in first.__dataclass_fields__:
        object.__setattr__(tampered, field, getattr(first, field))
    object.__setattr__(tampered, "source_baseline", "changed")

    result = verify_export_chain((tampered,))

    assert not result.valid
    assert "manifest_hash_invalid:0" in result.issues
