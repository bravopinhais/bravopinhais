from copy import deepcopy
from datetime import datetime

import pytest

from app.core.migration_batch_state import BatchApproval, BatchTransitionError
from app.core.migration_batch_state_postgres import PostgresBatchStateStore


HASH = "a" * 64


class FakeDatabase:
    def __init__(self):
        self.rows = {
            "batch-1": [
                "batch-1", HASH, "ci_ephemeral", "prepared",
                None, None, None, None,
            ]
        }

    def connect(self):
        return FakeConnection(self)


class FakeConnection:
    def __init__(self, db):
        self.db = db
        self.before = deepcopy(db.rows)
        self.statements = []
        self.closed = False

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        pass

    def rollback(self):
        self.db.rows = deepcopy(self.before)

    def close(self):
        self.closed = True


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection
        self.one = None
        self.rowcount = 1

    def execute(self, sql, params=()):
        db = self.connection.db
        query = " ".join(sql.split())
        self.connection.statements.append(query)
        if query.startswith("SELECT batch_id"):
            row = db.rows.get(params[0])
            self.one = tuple(row[:7]) if row else None
        elif query.startswith("UPDATE bravo_shadow.migration_batches"):
            status, approved_by, approved_at, approved_hash, finished_status, batch_id, manifest_hash, old_status = params
            row = db.rows.get(batch_id)
            if row and row[1] == manifest_hash and row[3] == old_status:
                row[3] = status
                row[4:7] = [approved_by, approved_at, approved_hash]
                row[7] = finished_status in {"applied", "verified", "failed", "rolled_back"}
                self.one = (batch_id,)
            else:
                self.one = None
        else:
            raise AssertionError(f"SQL não previsto: {query}")

    def fetchone(self):
        return self.one

    def close(self):
        pass


def setup_store():
    database = FakeDatabase()
    connection = database.connect()
    return database, connection, PostgresBatchStateStore(lambda: connection)


def approval():
    return BatchApproval(
        reviewer_id="reviewer@example.test",
        approved_at="2026-11-26T18:30:00-03:00",
        manifest_hash=HASH,
    )


def test_postgres_adapter_persists_approved_and_applied_states_under_lock():
    database, connection, store = setup_store()

    approved = store.transition("batch-1", "approved", approval=approval())
    applying = store.transition(
        "batch-1", "applying", expected_manifest_hash=HASH
    )
    applied = store.transition("batch-1", "applied")

    assert [approved.status, applying.status, applied.status] == [
        "approved", "applying", "applied"
    ]
    row = database.rows["batch-1"]
    assert row[3] == "applied"
    assert row[4] == "reviewer@example.test"
    assert row[6] == HASH
    assert row[7] is True
    assert "FOR UPDATE" in connection.statements[0]


def test_postgres_adapter_rejects_missing_batch_and_rolls_back():
    database, connection, store = setup_store()

    with pytest.raises(BatchTransitionError, match="batch_not_found"):
        store.transition("missing", "failed")

    assert database.rows["batch-1"][3] == "prepared"
    assert connection.closed is True


def test_postgres_adapter_rejects_partial_persisted_approval():
    database, _, store = setup_store()
    database.rows["batch-1"][4] = "reviewer@example.test"

    with pytest.raises(BatchTransitionError, match="stored_approval_incomplete"):
        store.transition("batch-1", "failed")


def test_postgres_adapter_rejects_hash_mismatch_without_changing_row():
    database, _, store = setup_store()
    before = deepcopy(database.rows["batch-1"])

    with pytest.raises(BatchTransitionError, match="approval_manifest_mismatch"):
        store.transition(
            "batch-1", "approved",
            approval=BatchApproval("reviewer", "2026-11-26T18:30:00-03:00", "b" * 64),
        )

    assert database.rows["batch-1"] == before


def test_postgres_adapter_uses_compare_and_set_on_update():
    database, connection, store = setup_store()
    store.transition("batch-1", "failed")

    update = next(
        statement for statement in connection.statements
        if statement.startswith("UPDATE bravo_shadow.migration_batches")
    )
    assert "AND manifest_hash = %s AND status = %s" in update
    assert database.rows["batch-1"][3] == "failed"


def test_postgres_adapter_rolls_back_when_update_loses_race():
    database = FakeDatabase()
    database.rows["batch-1"][3] = "failed"
    connection = database.connect()
    store = PostgresBatchStateStore(lambda: connection)
    before = deepcopy(database.rows)

    with pytest.raises(BatchTransitionError, match="invalid_status_transition"):
        store.transition("batch-1", "approved", approval=approval())

    assert database.rows == before


def test_postgres_adapter_persists_needs_review_as_terminal_state():
    database, connection, store = setup_store()
    store.transition("batch-1", "failed")
    # Use a fresh approved/applying batch to model an interrupted apply.
    database.rows["batch-1"][3] = "approved"
    database.rows["batch-1"][4:7] = [
        "reviewer@example.test", datetime(2026, 11, 26, 18, 30), HASH
    ]
    store.transition("batch-1", "applying", expected_manifest_hash=HASH)
    reviewed = store.transition("batch-1", "needs_review")

    assert reviewed.status == "needs_review"
    assert database.rows["batch-1"][3] == "needs_review"
    update = next(
        statement for statement in connection.statements
        if statement.startswith("UPDATE bravo_shadow.migration_batches")
    )
    assert "needs_review" in update or "finished_at = CASE" in update
