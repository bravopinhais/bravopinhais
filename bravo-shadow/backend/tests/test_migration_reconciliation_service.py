from app.core.migration_identity import SourceIdentity
from app.core.migration_reconciliation import SourceSnapshotRecord
from app.core.migration_reconciliation_service import reconcile_postgres_provenance


class FakeCursor:
    def __init__(self, rows):
        self.rows = rows
        self.statements = []
        self.closed = False

    def execute(self, statement):
        self.statements.append(" ".join(statement.split()))

    def fetchall(self):
        return self.rows

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self, rows):
        self.fake_cursor = FakeCursor(rows)

    def cursor(self):
        return self.fake_cursor


def source(legacy_id, digest="a" * 64):
    return SourceSnapshotRecord(
        SourceIdentity("legacy-bravo", "moradores", legacy_id), digest
    )


def provenance_row(legacy_id, destination_id, digest="a" * 64):
    return (
        "legacy-bravo",
        "moradores",
        legacy_id,
        digest,
        "residents",
        destination_id,
    )


def test_service_reconciles_using_read_only_snapshot_and_closes_cursor():
    connection = FakeConnection([provenance_row("m1", "r1")])

    report = reconcile_postgres_provenance(
        connection=connection,
        source_records=(source("m1"),),
    )

    assert report.valid is True
    assert report.matched == 1
    assert connection.fake_cursor.statements[0] == "SET TRANSACTION READ ONLY"
    assert connection.fake_cursor.statements[1].startswith("SELECT")
    assert connection.fake_cursor.closed is True


def test_service_reports_missing_mapping_without_writing():
    connection = FakeConnection([])

    report = reconcile_postgres_provenance(
        connection=connection,
        source_records=(source("m1"),),
    )

    assert report.valid is False
    assert report.missing_mapping == 1
    assert len(connection.fake_cursor.statements) == 2
    assert connection.fake_cursor.closed is True


def test_service_rejects_mutable_or_invalid_source_inventory_before_database_read():
    connection = FakeConnection([])

    try:
        reconcile_postgres_provenance(connection=connection, source_records=[])
    except TypeError as exc:
        assert "tupla imutável" in str(exc)
    else:
        raise AssertionError("esperava TypeError")

    try:
        reconcile_postgres_provenance(connection=connection, source_records=("bad",))
    except TypeError as exc:
        assert "tipo inválido" in str(exc)
    else:
        raise AssertionError("esperava TypeError")

    assert connection.fake_cursor.statements == []
