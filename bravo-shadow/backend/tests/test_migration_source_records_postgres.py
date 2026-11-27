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
        self.verified_batches = set()
        self.last_verified = {}

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
        elif query.startswith("UPDATE bravo_shadow.migration_source_records AS source"):
            (
                batch_id, source_system, source_collection, legacy_id,
                destination_collection, destination_id, record_hash,
                verified_batch_id, verified_source_system,
            ) = params
            stored = self.connection.records.get(
                (source_system, source_collection, legacy_id)
            )
            eligible = (
                stored is not None
                and stored[:3] == (
                    destination_collection, destination_id, record_hash
                )
                and (verified_batch_id, verified_source_system)
                in self.connection.verified_batches
                and batch_id == verified_batch_id
            )
            self.result = (source_system,) if eligible else None
            if eligible:
                self.connection.last_verified[
                    (source_system, source_collection, legacy_id)
                ] = batch_id
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



def test_mark_verified_advances_only_after_matching_batch_is_verified():
    connection = FakeConnection()
    store = PostgresSourceRecordStore()
    store.record(connection, link())
    connection.verified_batches.add(("batch-synthetic-002", "legacy"))

    store.mark_verified(
        connection,
        source_system="legacy",
        source_collection="fornecedores",
        legacy_id="fornecedor-17",
        destination_collection="suppliers",
        destination_id="shadow-900",
        source_record_hash=HASH,
        batch_id="batch-synthetic-002",
    )

    assert connection.last_verified[
        ("legacy", "fornecedores", "fornecedor-17")
    ] == "batch-synthetic-002"
    assert "updated_at = now()" in connection.statements[-1]
    assert "batch.status = 'verified'" in connection.statements[-1]


@pytest.mark.parametrize(
    "changes",
    [
        {"source_record_hash": "b" * 64},
        {"destination_id": "shadow-999"},
        {"batch_id": "batch-not-verified"},
    ],
)
def test_mark_verified_rejects_unmatched_provenance_or_unverified_batch(changes):
    connection = FakeConnection()
    store = PostgresSourceRecordStore()
    store.record(connection, link())
    connection.verified_batches.add(("batch-synthetic-002", "legacy"))
    values = dict(
        source_system="legacy",
        source_collection="fornecedores",
        legacy_id="fornecedor-17",
        destination_collection="suppliers",
        destination_id="shadow-900",
        source_record_hash=HASH,
        batch_id="batch-synthetic-002",
    )
    values.update(changes)

    with pytest.raises(
        SourceRecordConflict,
        match="source_record_verification_not_eligible",
    ):
        store.mark_verified(connection, **values)

    assert connection.last_verified == {}
