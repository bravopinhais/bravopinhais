from __future__ import annotations

from copy import deepcopy

import pytest

from app.core.migration_review import ReviewValidationError
from app.core.migration_review_postgres import PostgresReviewLedgerStore
from test_migration_decisions import setup_batch
from app.core.migration_decisions import build_decision_register


class FakeDatabase:
    def __init__(self):
        self.batches = {}
        self.decisions = {}
        self.events = []

    def connect(self):
        return FakeConnection(self)


class FakeConnection:
    def __init__(self, database):
        self.database = database
        self.before = deepcopy((database.batches, database.decisions, database.events))
        self.closed = False
        self.statements = []

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        pass

    def rollback(self):
        self.database.batches, self.database.decisions, self.database.events = deepcopy(self.before)

    def close(self):
        self.closed = True


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection
        self.rows = []
        self.one = None

    def execute(self, sql, params=()):
        db = self.connection.database
        query = " ".join(sql.split())
        self.connection.statements.append(query)

        if query.startswith("INSERT INTO bravo_shadow.migration_review_batches"):
            batch_key, manifest_hash = params
            db.batches.setdefault(batch_key, manifest_hash)
        elif query.startswith("SELECT manifest_hash FROM bravo_shadow.migration_review_batches"):
            batch_key = params[0]
            value = db.batches.get(batch_key)
            self.one = (value,) if value is not None else None
        elif query.startswith("INSERT INTO bravo_shadow.migration_review_decisions"):
            decision_id, batch_key, manifest_hash, kind, status, requires_human, automatic_action = params
            db.decisions.setdefault(decision_id, (
                batch_key, manifest_hash, decision_id, kind, status,
                requires_human, automatic_action,
            ))
        elif query.startswith("SELECT decision_id, manifest_hash, decision_kind, decision_status"):
            batch_key = params[0]
            self.rows = sorted(
                (row[2], row[1], row[3], row[4], row[5], row[6])
                for row in db.decisions.values()
                if row[0] == batch_key
            )
        elif query.startswith("SELECT batch_key, manifest_hash FROM bravo_shadow.migration_review_decisions"):
            batch_key, decision_id = params
            row = db.decisions.get(decision_id)
            self.one = (row[0], row[1]) if row and row[0] == batch_key else None
        elif query.startswith("SELECT event_id, decision_id, manifest_hash, version"):
            (batch_key,) = params
            self.rows = sorted(
                [
                    (row[0], row[2], row[3], row[4], row[5], row[6], row[7], row[8])
                    for row in db.events
                    if row[1] == batch_key
                ],
                key=lambda row: (row[1], row[3]),
            )
        elif query.startswith("SELECT event_id FROM bravo_shadow.migration_review_events"):
            (event_id,) = params
            self.one = (event_id,) if any(row[0] == event_id for row in db.events) else None
        elif query.startswith("SELECT COALESCE(MAX(version), 0)"):
            batch_key, decision_id = params
            versions = [
                row[4] for row in db.events
                if row[1] == batch_key and row[2] == decision_id
            ]
            self.one = (max(versions, default=0),)
        elif query.startswith("INSERT INTO bravo_shadow.migration_review_events"):
            db.events.append(tuple(params))
            if "RETURNING event_id" in query:
                self.one = (params[0],)
        else:
            raise AssertionError(f"SQL não previsto no teste: {query}")

    def fetchone(self):
        return self.one

    def fetchall(self):
        return self.rows

    def close(self):
        pass


def setup_store():
    _, _, preflight, manifest = setup_batch()
    register = build_decision_register(manifest, preflight)
    database = FakeDatabase()
    return register, register.pending[0].decision_id, database, PostgresReviewLedgerStore(database.connect)


def event_args(decision_id, event_id, expected_version):
    return dict(
        event_id=event_id,
        decision_id=decision_id,
        expected_version=expected_version,
        reviewer_id="reviewer@example.test",
        choice="keep_blocked",
        rationale="Manter bloqueado até conferência.",
        reviewed_at="2026-11-26T16:00:00-03:00",
    )


def test_postgres_adapter_initializes_loads_and_appends_history():
    register, decision_id, database, store = setup_store()

    empty = store.initialize(register)
    assert empty.events == ()
    first = store.append(register, **event_args(decision_id, "pg-evt-1", 0))
    second = store.append(register, **event_args(decision_id, "pg-evt-2", 1))

    assert [event.version for event in second.history_for(decision_id)] == [1, 2]
    assert [event.event_id for event in store.load(register).events] == ["pg-evt-1", "pg-evt-2"]
    assert len(database.events) == 2
    assert first.events[0].version == 1


def test_postgres_adapter_requires_explicit_initialization():
    register, _, _, store = setup_store()

    with pytest.raises(ReviewValidationError, match="review_batch_not_initialized"):
        store.load(register)


def test_postgres_adapter_rejects_stale_version_without_writing():
    register, decision_id, database, store = setup_store()
    store.initialize(register)
    store.append(register, **event_args(decision_id, "pg-evt-1", 0))

    with pytest.raises(ReviewValidationError, match="stale_review_version"):
        store.append(register, **event_args(decision_id, "pg-evt-stale", 0))

    assert len(database.events) == 1


def test_postgres_adapter_rejects_manifest_rebinding():
    from dataclasses import replace

    register, _, database, store = setup_store()
    store.initialize(register)
    changed = replace(register, manifest_hash="f" * 64)

    with pytest.raises(ReviewValidationError, match="stored_batch_manifest_mismatch"):
        store.load(changed)

    assert database.batches[register.batch_id] == register.manifest_hash


def test_postgres_adapter_detects_changed_decision_snapshot():
    register, _, database, store = setup_store()
    store.initialize(register)
    decision_id = register.pending[0].decision_id
    row = database.decisions[decision_id]
    database.decisions[decision_id] = (row[0], row[1], row[2], row[3], "tampered", row[5], row[6])

    with pytest.raises(ReviewValidationError, match="stored_decision_snapshot_mismatch"):
        store.load(register)

def test_postgres_adapter_rejects_events_bound_to_another_manifest():
    register, decision_id, database, store = setup_store()
    store.initialize(register)
    store.append(register, **event_args(decision_id, "pg-evt-valid", 0))

    stored = database.events[0]
    database.events[0] = (
        stored[0], stored[1], stored[2], "e" * 64,
        stored[4], stored[5], stored[6], stored[7], stored[8],
    )

    with pytest.raises(ReviewValidationError, match="stored_event_manifest_mismatch"):
        store.load(register)


def test_postgres_adapter_does_not_coerce_corrupt_event_version():
    register, decision_id, database, store = setup_store()
    store.initialize(register)
    store.append(register, **event_args(decision_id, "pg-evt-version", 0))

    stored = database.events[0]
    database.events[0] = (
        stored[0], stored[1], stored[2], stored[3], True,
        stored[5], stored[6], stored[7], stored[8],
    )

    with pytest.raises(ReviewValidationError, match="stored_ledger_binding_or_integrity_error"):
        store.load(register)

def test_postgres_adapter_rejects_null_review_timestamp():
    register, decision_id, database, store = setup_store()
    store.initialize(register)
    store.append(register, **event_args(decision_id, "pg-evt-null-time", 0))

    stored = database.events[0]
    database.events[0] = (
        stored[0], stored[1], stored[2], stored[3], stored[4],
        stored[5], stored[6], stored[7], None,
    )

    with pytest.raises(ReviewValidationError, match="stored_ledger_binding_or_integrity_error"):
        store.load(register)



def test_postgres_adapter_rejects_event_id_already_used_in_another_batch():
    register, decision_id, database, store = setup_store()
    store.initialize(register)
    database.events.append((
        "globally-used-event", "another-decision", "another-batch",
        register.manifest_hash, 1, "other@example.test", "keep_blocked",
        "Evento de outro lote.", "2026-11-26T16:00:00-03:00",
    ))

    with pytest.raises(ReviewValidationError, match="duplicate_review_event_id"):
        store.append(register, **event_args(decision_id, "globally-used-event", 0))

    assert len(database.events) == 1



def test_postgres_adapter_initialization_is_idempotent_for_same_snapshot():
    register, _, database, store = setup_store()

    first = store.initialize(register)
    second = store.initialize(register)

    assert first == second
    assert len(database.batches) == 1
    assert len(database.decisions) == len(register.pending)


def test_postgres_adapter_rejects_duplicate_decision_ids_before_writing():
    from dataclasses import replace

    register, _, database, store = setup_store()
    duplicated = replace(
        register,
        pending=register.pending + (register.pending[0],),
        pending_count=register.pending_count + 1,
    )

    with pytest.raises(ReviewValidationError, match="duplicate_decision_id_in_register"):
        store.initialize(duplicated)

    assert database.batches == {}
    assert database.decisions == {}
    assert database.events == []



def test_postgres_adapter_locks_batch_before_decision_during_append():
    register, decision_id, database, store = setup_store()
    store.initialize(register)
    connection = database.connect()

    class CapturingStore(PostgresReviewLedgerStore):
        def __init__(self):
            super().__init__(lambda: connection)

    CapturingStore().append(register, **event_args(decision_id, "lock-order-event", 0))

    batch_lock = next(
        index for index, statement in enumerate(connection.statements)
        if statement.startswith("SELECT manifest_hash FROM bravo_shadow.migration_review_batches")
        and "FOR UPDATE" in statement
    )
    decision_lock = next(
        index for index, statement in enumerate(connection.statements)
        if statement.startswith("SELECT batch_key, manifest_hash FROM bravo_shadow.migration_review_decisions")
        and "FOR UPDATE" in statement
    )
    assert batch_lock < decision_lock


def test_postgres_review_store_preserves_query_error_when_cursor_close_fails():
    original_error = RuntimeError("query failed")

    class FailingCursor:
        def execute(self, sql, params=()):
            raise original_error

        def close(self):
            raise OSError("cursor close failed")

    class Connection:
        def cursor(self):
            return FailingCursor()

    with pytest.raises(RuntimeError) as raised:
        PostgresReviewLedgerStore._run(Connection(), "SELECT 1")

    assert raised.value is original_error
    assert any(
        "fechamento do cursor" in note
        for note in getattr(original_error, "__notes__", ())
    )


def test_postgres_review_store_close_helper_preserves_primary_fetch_error():
    original_error = RuntimeError("fetch failed")

    class FailingCursor:
        def close(self):
            raise OSError("cursor close failed")

    with pytest.raises(RuntimeError) as raised:
        try:
            raise original_error
        except RuntimeError:
            PostgresReviewLedgerStore._close_cursor(FailingCursor())
            raise

    assert raised.value is original_error
    assert any(
        "fechamento do cursor" in note
        for note in getattr(original_error, "__notes__", ())
    )
