import pytest

from app.core.migration_identity import SourceIdentity
from app.core.migration_reconciliation import SourceSnapshotRecord
from app.core.migration_source_snapshot import SourceSnapshot


def record(source_system="legacy-bravo", legacy_id="m1"):
    return SourceSnapshotRecord(
        SourceIdentity(source_system, "moradores", legacy_id), "a" * 64
    )


def snapshot(records=(record(),), **overrides):
    values = {
        "source_system": "legacy-bravo",
        "source_baseline": "legacy-export-2026-11-26",
        "snapshot_hash": "b" * 64,
        "exported_at": "2026-11-26T18:00:00-03:00",
        "records": records,
    }
    values.update(overrides)
    return SourceSnapshot(**values)


def test_source_snapshot_accepts_valid_immutable_inventory():
    result = snapshot()

    assert result.source_system == "legacy-bravo"
    assert result.records == (record(),)


@pytest.mark.parametrize("field,value", [
    ("source_system", ""),
    ("source_baseline", ""),
    ("exported_at", ""),
    ("snapshot_hash", "not-a-sha256"),
])
def test_source_snapshot_rejects_missing_or_invalid_metadata(field, value):
    with pytest.raises(ValueError):
        snapshot(**{field: value})


def test_source_snapshot_rejects_mutable_or_invalid_record_collection():
    with pytest.raises(TypeError, match="tupla imutável"):
        snapshot(records=[record()])
    with pytest.raises(TypeError, match="tipo inválido"):
        snapshot(records=("not-a-record",))


def test_source_snapshot_rejects_records_from_another_source_system():
    with pytest.raises(ValueError, match="source_system declarado"):
        snapshot(records=(record(source_system="other-system"),))
