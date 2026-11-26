from app.core.migration_provenance_snapshot_postgres import (
    PostgresProvenanceSnapshotReader,
    ProvenanceSnapshotReadError,
)


class FakeCursor:
    def __init__(self, rows=(), fail_on=None):
        self.rows = rows
        self.fail_on = fail_on
        self.calls = []
        self.closed = False

    def execute(self, sql, params=None):
        normalized = " ".join(sql.split())
        self.calls.append(normalized)
        if self.fail_on and self.fail_on in normalized:
            raise RuntimeError("database error")

    def fetchall(self):
        return self.rows

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self, cursor):
        self.fake_cursor = cursor

    def cursor(self):
        return self.fake_cursor


def test_reader_sets_read_only_before_select_and_returns_sorted_inventory():
    cursor = FakeCursor(
        rows=[
            ("legacy", "residents", "r1", "a" * 64, "residents", "new-1"),
            ("legacy", "residents", "r2", "b" * 64, "residents", "new-2"),
        ]
    )
    connection = FakeConnection(cursor)

    result = PostgresProvenanceSnapshotReader().read(connection)

    assert cursor.calls[0] == "SET TRANSACTION READ ONLY"
    assert "FROM bravo_shadow.migration_source_records" in cursor.calls[1]
    assert "ORDER BY source_system, source_collection, legacy_id" in cursor.calls[1]
    assert [item.identity.legacy_id for item in result] == ["r1", "r2"]
    assert result[0].destination_id == "new-1"
    assert cursor.closed is True


def test_reader_returns_empty_snapshot_without_writes_or_commit():
    cursor = FakeCursor(rows=[])
    connection = FakeConnection(cursor)

    result = PostgresProvenanceSnapshotReader().read(connection)

    assert result == ()
    assert len(cursor.calls) == 2
    assert cursor.closed is True


def test_reader_wraps_database_failures_and_closes_cursor():
    cursor = FakeCursor(fail_on="FROM bravo_shadow.migration_source_records")
    connection = FakeConnection(cursor)

    try:
        PostgresProvenanceSnapshotReader().read(connection)
    except ProvenanceSnapshotReadError as exc:
        assert str(exc) == "provenance_snapshot_read_failed"
    else:
        raise AssertionError("expected read failure")

    assert cursor.closed is True


def test_reader_rejects_malformed_provenance_rows():
    cursor = FakeCursor(
        rows=[("legacy", "residents", "r1", "bad-hash", "residents", "new-1")]
    )

    try:
        PostgresProvenanceSnapshotReader().read(FakeConnection(cursor))
    except ProvenanceSnapshotReadError as exc:
        assert str(exc) == "provenance_snapshot_invalid_row"
    else:
        raise AssertionError("expected invalid snapshot row")
