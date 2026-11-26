import pytest

from app.core.migration_source_records_postgres import (
    PostgresSourceRecordStore,
    SourceRecordConflict,
    SourceRecordLink,
)


HASH = "a" * 64


class FakeConnection:
    def __init__(self):
        self.records = {}
        self.statements = []

    def cursor(self):
        return FakeCursor(self)


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection
        self.result = None

    def execute(self, sql, params):
        query = " ".join(sql.split())
        self.connection.statements.append(query)
        key = tuple(params[:3])
        if query.startswith("INSERT INTO bravo_shadow.migration_source_records"):
            link = tuple(params[3:6])
            if key not in self.connection.records:
                self.connection.records[key] = link + (params[6],)
                self.result = (params[0],)
            else:
                self.result = None
        elif query.startswith("SELECT destination_collection"):
            stored = self.connection.records.get(key)
            self.result = stored[:3] if stored else None
        else:
            raise AssertionError(f"SQL não previsto: {query}")

    def fetchone(self):
        return self.result

    def close(self):
        pass


def link(**changes):
    values = dict(
        source_system="legacy",
        source_collection="fornecedores",
        legacy_id="fornecedor-17",
        destination_collection="suppliers",
        destination_id="shadow-900",
        source_record_hash=HASH,
        batch_id="batch-synthetic-001",
    )
    values.update(changes)
    return SourceRecordLink(**values)


def test_source_record_insert_and_exact_replay_are_idempotent():
    connection = FakeConnection()
    store = PostgresSourceRecordStore()

    store.record(connection, link())
    store.record(connection, link(batch_id="batch-synthetic-002"))

    row = connection.records[("legacy", "fornecedores", "fornecedor-17")]
    assert row == ("suppliers", "shadow-900", HASH, "batch-synthetic-001")
    assert "FOR UPDATE" in connection.statements[-1]


@pytest.mark.parametrize(
    "changes",
    [
        {"destination_id": "shadow-901"},
        {"destination_collection": "other_table"},
        {"source_record_hash": "b" * 64},
    ],
)
def test_source_record_conflicting_replay_fails_closed(changes):
    connection = FakeConnection()
    store = PostgresSourceRecordStore()
    store.record(connection, link())

    with pytest.raises(
        SourceRecordConflict,
        match="source_record_identity_or_content_conflict",
    ):
        store.record(connection, link(**changes))


def test_source_record_rejects_malformed_hash_and_empty_fields():
    connection = FakeConnection()
    store = PostgresSourceRecordStore()

    with pytest.raises(SourceRecordConflict, match="source_record_hash_invalid"):
        store.record(connection, link(source_record_hash="not-a-hash"))
    with pytest.raises(SourceRecordConflict, match="source_record_fields_required"):
        store.record(connection, link(legacy_id=" "))

    assert connection.records == {}
