from app.core.migration_identity import SourceIdentity
from app.core.migration_reconciliation import (
    DestinationProvenance,
    SourceSnapshotRecord,
    reconcile_source_and_shadow,
)


def source(legacy_id, digest="a" * 64):
    return SourceSnapshotRecord(
        SourceIdentity("legacy-bravo", "moradores", legacy_id), digest
    )


def mapping(legacy_id, destination_id, digest="a" * 64, collection="residents"):
    return DestinationProvenance(
        SourceIdentity("legacy-bravo", "moradores", legacy_id),
        digest,
        collection,
        destination_id,
    )


def test_reconciliation_accepts_exact_one_to_one_inventory():
    report = reconcile_source_and_shadow(
        (source("m1"), source("m2", "b" * 64)),
        (mapping("m1", "r1"), mapping("m2", "r2", "b" * 64)),
    )

    assert report.valid is True
    assert report.matched == 2
    assert report.missing_mapping == 0
    assert report.issues == ()


def test_reconciliation_reports_missing_changed_and_orphaned_links():
    report = reconcile_source_and_shadow(
        (source("m1"), source("m2", "b" * 64)),
        (mapping("m2", "r2", "c" * 64), mapping("old", "r-old")),
    )

    assert report.valid is False
    assert report.matched == 0
    assert report.missing_mapping == 1
    assert report.changed_source_hash == 1
    assert report.orphaned_mapping == 1


def test_reconciliation_reports_duplicate_source_and_destination():
    report = reconcile_source_and_shadow(
        (source("m1"), source("m1")),
        (mapping("m1", "same-destination"), mapping("m2", "same-destination")),
    )

    assert report.valid is False
    assert report.duplicate_source_mapping == 2
    assert report.duplicate_destination == 1


def test_reconciliation_is_read_only_and_deterministic():
    sources = (source("m2", "b" * 64), source("m1"))
    mappings = (mapping("m1", "r1"), mapping("m2", "r2", "b" * 64))

    first = reconcile_source_and_shadow(sources, mappings)
    second = reconcile_source_and_shadow(sources, mappings)

    assert first == second
    assert first.valid is True
    assert first.matched == 2
