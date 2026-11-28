"""Integração concorrente real com PostgreSQL descartável (opt-in)."""
from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from urllib.parse import urlparse
from uuid import uuid4

import psycopg
import pytest

from app.core.migration_decisions import build_decision_register
from app.core.migration_manifest import build_migration_manifest
from app.core.migration_preflight import run_migration_preflight
from app.core.migration_report import build_preflight_report
from app.core.migration_review import ReviewValidationError
from app.core.migration_review_postgres import PostgresReviewLedgerStore
from test_migration_decisions import setup_batch


DATABASE_URL = os.getenv("BRAVO_SHADOW_TEST_DATABASE_URL")


def _guard_test_database(url: str) -> None:
    if os.getenv("BRAVO_SHADOW_ALLOW_DESTRUCTIVE_TEST_DATABASE") != "1":
        raise RuntimeError(
            "Integração destrutiva bloqueada: defina "
            "BRAVO_SHADOW_ALLOW_DESTRUCTIVE_TEST_DATABASE=1 apenas para "
            "o banco descartável dedicado."
        )
    parsed = urlparse(url)
    database = parsed.path.lstrip("/")
    if database != "bravo_shadow_test":
        raise RuntimeError(
            "BRAVO_SHADOW_TEST_DATABASE_URL precisa apontar exatamente para "
            "o banco descartável bravo_shadow_test."
        )
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise RuntimeError("A URL de integração precisa usar PostgreSQL.")
    if parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError("Os testes só podem conectar a PostgreSQL local/descartável.")


@pytest.fixture
def postgres_database():
    if not DATABASE_URL:
        pytest.skip("PostgreSQL real não configurado; testes de integração opt-in.")

    _guard_test_database(DATABASE_URL)
    root = Path(__file__).resolve().parents[2]
    schema_sql = root / "docs" / "sql-controle-revisao-migracao-rascunho.sql"

    with psycopg.connect(DATABASE_URL, autocommit=True) as connection:
        for role in ("anon", "authenticated", "service_role"):
            existing_role = connection.execute(
                "SELECT 1 FROM pg_roles WHERE rolname = %s", (role,)
            ).fetchone()
            if existing_role is None:
                connection.execute(f'CREATE ROLE "{role}" NOLOGIN')
        connection.execute("DROP SCHEMA IF EXISTS bravo_shadow CASCADE")
        connection.execute("DROP ROLE IF EXISTS bravo_shadow_runtime_test")
        connection.execute(
            "CREATE ROLE bravo_shadow_runtime_test LOGIN "
            "PASSWORD 'bravo-shadow-test-only'"
        )
        connection.execute(schema_sql.read_text(encoding="utf-8"), prepare=False)

    yield DATABASE_URL

    with psycopg.connect(DATABASE_URL, autocommit=True) as connection:
        connection.execute("DROP SCHEMA IF EXISTS bravo_shadow CASCADE")
        connection.execute("DROP ROLE IF EXISTS bravo_shadow_runtime_test")


def _register():
    _, _, preflight, manifest = setup_batch()
    return build_decision_register(manifest, preflight)



def _register_for_distinct_batch():
    envelope, candidates, _, _ = setup_batch()
    envelope = dict(envelope)
    envelope["sourceBaseline"] = "synthetic-decisions-second-batch"
    envelope["snapshotHash"] = "c" * 64
    preflight = run_migration_preflight(envelope, candidates)
    report = build_preflight_report(envelope, candidates, preflight)
    manifest = build_migration_manifest(
        envelope,
        candidates,
        preflight,
        report,
        environment="shadow-test",
        importer_version="1.0.0",
        mapping_version="1.0.0",
        created_at="2026-11-26T15:00:00-03:00",
    )
    return build_decision_register(manifest, preflight)


def _event_args(decision_id: str, event_id: str) -> dict:
    return {
        "event_id": event_id,
        "decision_id": decision_id,
        "expected_version": 0,
        "reviewer_id": "integration-reviewer@example.test",
        "choice": "keep_blocked",
        "rationale": "Teste concorrente com dados sintéticos.",
        "reviewed_at": "2026-11-26T16:00:00-03:00",
    }


def test_two_parallel_appends_same_version_commit_exactly_one(postgres_database):
    register = _register()
    decision_id = register.pending[0].decision_id
    store = PostgresReviewLedgerStore(
        lambda: psycopg.connect(postgres_database)
    )
    store.initialize(register)
    barrier = Barrier(2)

    def append(event_id: str):
        barrier.wait(timeout=10)
        try:
            store.append(
                register, **_event_args(decision_id, event_id)
            )
            return "committed"
        except ReviewValidationError as error:
            return str(error)

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(append, (f"parallel-{uuid4()}", f"parallel-{uuid4()}")))

    assert outcomes.count("committed") == 1
    assert outcomes.count("stale_review_version") == 1
    ledger = store.load(register)
    assert len(ledger.history_for(decision_id)) == 1
    assert ledger.history_for(decision_id)[0].version == 1


def test_parallel_initialization_is_idempotent(postgres_database):
    register = _register()
    store = PostgresReviewLedgerStore(
        lambda: psycopg.connect(postgres_database)
    )
    barrier = Barrier(2)

    def initialize():
        barrier.wait(timeout=10)
        return store.initialize(register)

    with ThreadPoolExecutor(max_workers=2) as pool:
        ledgers = list(pool.map(lambda _: initialize(), range(2)))

    assert ledgers[0] == ledgers[1]
    assert store.load(register).events == ()


def test_parallel_appends_to_different_decisions_preserve_both_events(postgres_database):
    register = _register()
    assert len(register.pending) >= 2, "Fixture sintética precisa de duas decisões."
    store = PostgresReviewLedgerStore(lambda: psycopg.connect(postgres_database))
    store.initialize(register)
    barrier = Barrier(2)

    def append(decision_id: str, event_id: str):
        barrier.wait(timeout=10)
        return store.append(register, **_event_args(decision_id, event_id))

    items = (
        (register.pending[0].decision_id, f"distinct-{uuid4()}"),
        (register.pending[1].decision_id, f"distinct-{uuid4()}"),
    )
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda item: append(*item), items))

    assert all(len(result.events) >= 1 for result in results)
    ledger = store.load(register)
    assert len(ledger.events) == 2
    assert {event.decision_id for event in ledger.events} == {items[0][0], items[1][0]}


def test_event_id_is_unique_across_decisions_in_batch(postgres_database):
    register = _register()
    assert len(register.pending) >= 2, "Fixture sintética precisa de duas decisões."
    store = PostgresReviewLedgerStore(lambda: psycopg.connect(postgres_database))
    store.initialize(register)
    shared_event_id = f"shared-{uuid4()}"
    store.append(register, **_event_args(register.pending[0].decision_id, shared_event_id))
    with pytest.raises(ReviewValidationError, match="duplicate_review_event_id"):
        store.append(register, **_event_args(register.pending[1].decision_id, shared_event_id))
    ledger = store.load(register)
    assert len(ledger.events) == 1
    assert ledger.events[0].event_id == shared_event_id


def test_failed_event_insert_rolls_back_and_allows_retry(postgres_database):
    register = _register()
    decision_id = register.pending[0].decision_id
    store = PostgresReviewLedgerStore(lambda: psycopg.connect(postgres_database))
    store.initialize(register)
    event_id = f"rollback-{uuid4()}"
    with psycopg.connect(postgres_database, autocommit=True) as connection:
        connection.execute("""
            CREATE FUNCTION bravo_shadow.reject_test_event() RETURNS trigger
            LANGUAGE plpgsql AS $$
            BEGIN
                IF NEW.event_id LIKE 'rollback-%' THEN
                    RAISE EXCEPTION 'forced integration rollback';
                END IF;
                RETURN NEW;
            END;
            $$
        """)
        connection.execute("""
            CREATE TRIGGER reject_test_event_before_insert
            BEFORE INSERT ON bravo_shadow.migration_review_events
            FOR EACH ROW EXECUTE FUNCTION bravo_shadow.reject_test_event()
        """)

    with pytest.raises(psycopg.Error, match="forced integration rollback"):
        store.append(register, **_event_args(decision_id, event_id))

    assert store.load(register).history_for(decision_id) == ()

    with psycopg.connect(postgres_database, autocommit=True) as connection:
        connection.execute("DROP TRIGGER reject_test_event_before_insert ON bravo_shadow.migration_review_events")
        connection.execute("DROP FUNCTION bravo_shadow.reject_test_event()")

    retried = store.append(register, **_event_args(decision_id, event_id))
    assert [event.event_id for event in retried.history_for(decision_id)] == [event_id]


def test_deferred_commit_failure_rolls_back_and_allows_retry(postgres_database):
    register = _register()
    decision_id = register.pending[0].decision_id
    store = PostgresReviewLedgerStore(lambda: psycopg.connect(postgres_database))
    store.initialize(register)
    event_id = f"commit-fail-{uuid4()}"

    with psycopg.connect(postgres_database, autocommit=True) as connection:
        connection.execute("""
            CREATE FUNCTION bravo_shadow.reject_commit_event() RETURNS trigger
            LANGUAGE plpgsql AS $$
            BEGIN
                IF NEW.event_id LIKE 'commit-fail-%' THEN
                    RAISE EXCEPTION 'forced deferred commit failure';
                END IF;
                RETURN NEW;
            END;
            $$
        """)
        connection.execute("""
            CREATE CONSTRAINT TRIGGER reject_commit_event_at_commit
            AFTER INSERT ON bravo_shadow.migration_review_events
            DEFERRABLE INITIALLY DEFERRED
            FOR EACH ROW EXECUTE FUNCTION bravo_shadow.reject_commit_event()
        """)

    try:
        with pytest.raises(psycopg.Error, match="forced deferred commit failure"):
            store.append(register, **_event_args(decision_id, event_id))

        assert store.load(register).history_for(decision_id) == ()
    finally:
        with psycopg.connect(postgres_database, autocommit=True) as connection:
            connection.execute(
                "DROP TRIGGER IF EXISTS reject_commit_event_at_commit "
                "ON bravo_shadow.migration_review_events"
            )
            connection.execute(
                "DROP FUNCTION IF EXISTS bravo_shadow.reject_commit_event()"
            )

    retried = store.append(register, **_event_args(decision_id, event_id))
    assert [event.event_id for event in retried.history_for(decision_id)] == [event_id]


def test_event_id_is_unique_across_batches(postgres_database):
    first_register = _register()
    second_register = _register_for_distinct_batch()
    assert first_register.batch_id != second_register.batch_id
    assert first_register.pending[0].decision_id != second_register.pending[0].decision_id

    store = PostgresReviewLedgerStore(lambda: psycopg.connect(postgres_database))
    store.initialize(first_register)
    store.initialize(second_register)

    shared_event_id = f"cross-batch-{uuid4()}"
    first_decision_id = first_register.pending[0].decision_id
    second_decision_id = second_register.pending[0].decision_id
    store.append(
        first_register,
        **_event_args(first_decision_id, shared_event_id),
    )

    with pytest.raises(ReviewValidationError, match="duplicate_review_event_id"):
        store.append(
            second_register,
            **_event_args(second_decision_id, shared_event_id),
        )

    assert len(store.load(first_register).events) == 1
    assert store.load(second_register).events == ()


def test_parallel_cross_batch_duplicate_event_id_has_one_database_winner(postgres_database):
    first_register = _register()
    second_register = _register_for_distinct_batch()
    store = PostgresReviewLedgerStore(lambda: psycopg.connect(postgres_database))
    store.initialize(first_register)
    store.initialize(second_register)

    shared_event_id = f"parallel-cross-batch-{uuid4()}"
    barrier = Barrier(2)

    items = (
        (first_register, first_register.pending[0].decision_id),
        (second_register, second_register.pending[0].decision_id),
    )

    def append(item):
        register, decision_id = item
        barrier.wait(timeout=10)
        try:
            store.append(
                register,
                **_event_args(decision_id, shared_event_id),
            )
            return "committed"
        except ReviewValidationError as error:
            assert str(error) == "duplicate_review_event_id"
            return "unique_constraint_rejected"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(append, items))

    assert outcomes.count("committed") == 1
    assert outcomes.count("unique_constraint_rejected") == 1

    with psycopg.connect(postgres_database) as connection:
        persisted = connection.execute(
            "SELECT batch_key, decision_id FROM bravo_shadow.migration_review_events "
            "WHERE event_id = %s",
            (shared_event_id,),
        ).fetchall()

    assert len(persisted) == 1
    assert persisted[0][0] in {first_register.batch_id, second_register.batch_id}
    assert len(store.load(first_register).events) + len(store.load(second_register).events) == 1


def test_client_roles_are_denied_and_runtime_cannot_mutate_snapshots_or_ddl(postgres_database):
    register = _register()
    admin_store = PostgresReviewLedgerStore(lambda: psycopg.connect(postgres_database))
    admin_store.initialize(register)

    client_roles = ("anon", "authenticated", "service_role")
    with psycopg.connect(postgres_database, autocommit=True) as connection:
        for role in client_roles:
            connection.execute(
                f'ALTER ROLE "{role}" LOGIN PASSWORD %s',
                (f"{role}-shadow-test-only",),
            )

    admin_conninfo = psycopg.conninfo.conninfo_to_dict(postgres_database)
    admin_conninfo["dbname"] = "bravo_shadow_test"

    for role in client_roles:
        conninfo = dict(admin_conninfo)
        conninfo["user"] = role
        conninfo["password"] = f"{role}-shadow-test-only"
        with psycopg.connect(**conninfo) as connection:
            assert connection.execute(
                "SELECT session_user, current_user"
            ).fetchone() == (role, role)
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                connection.execute(
                    "SELECT * FROM bravo_shadow.migration_review_batches"
                )
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                connection.execute(
                    "INSERT INTO bravo_shadow.migration_review_events "
                    "(event_id, batch_key, decision_id, manifest_hash, version, "
                    "reviewer_id, choice, rationale, reviewed_at) "
                    "VALUES ('denied', 'batch', 'decision', 'hash', 1, "
                    "'actor', 'keep_blocked', 'test', now())"
                )

    runtime_conninfo = dict(admin_conninfo)
    runtime_conninfo["user"] = "bravo_shadow_runtime_test"
    runtime_conninfo["password"] = "bravo-shadow-test-only"
    with psycopg.connect(**runtime_conninfo) as runtime:
        assert runtime.execute(
            "SELECT session_user, current_user"
        ).fetchone() == (
            "bravo_shadow_runtime_test",
            "bravo_shadow_runtime_test",
        )
        for sql in (
            "UPDATE bravo_shadow.migration_review_batches "
            "SET manifest_hash = manifest_hash",
            "DELETE FROM bravo_shadow.migration_review_decisions",
            "INSERT INTO bravo_shadow.migration_review_batches "
            "(batch_key, manifest_hash) VALUES ('forbidden', 'hash')",
            "INSERT INTO bravo_shadow.migration_review_decisions "
            "(decision_id, batch_key, manifest_hash, decision_kind, "
            "decision_status, requires_human, automatic_action) "
            "VALUES ('forbidden', 'forbidden', 'hash', 'kind', 'pending', true, 'none')",
            "CREATE TABLE bravo_shadow.runtime_ddl_must_fail (id integer)",
        ):
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                runtime.execute(sql)


def test_runtime_append_works_without_update_on_snapshot_tables(postgres_database):
    register = _register()
    admin_store = PostgresReviewLedgerStore(lambda: psycopg.connect(postgres_database))
    admin_store.initialize(register)

    with psycopg.connect(postgres_database, autocommit=True) as connection:
        connection.execute("""
            GRANT USAGE ON SCHEMA bravo_shadow TO bravo_shadow_runtime_test
        """)
        connection.execute("""
            GRANT SELECT ON
                bravo_shadow.migration_review_batches,
                bravo_shadow.migration_review_decisions,
                bravo_shadow.migration_review_events
            TO bravo_shadow_runtime_test
        """)
        connection.execute("""
            GRANT INSERT ON bravo_shadow.migration_review_events
            TO bravo_shadow_runtime_test
        """)
        for table in (
            "migration_review_batches",
            "migration_review_decisions",
            "migration_review_events",
        ):
            connection.execute(
                f'ALTER TABLE bravo_shadow.{table} FORCE ROW LEVEL SECURITY'
            )
            connection.execute(
                f'CREATE POLICY runtime_select ON bravo_shadow.{table} '
                'FOR SELECT TO bravo_shadow_runtime_test USING (true)'
            )
        connection.execute("""
            CREATE POLICY runtime_insert ON bravo_shadow.migration_review_events
            FOR INSERT TO bravo_shadow_runtime_test WITH CHECK (true)
        """)
        privileges = connection.execute("""
            SELECT
                has_table_privilege(
                    'bravo_shadow_runtime_test',
                    'bravo_shadow.migration_review_batches', 'UPDATE'
                ),
                has_table_privilege(
                    'bravo_shadow_runtime_test',
                    'bravo_shadow.migration_review_decisions', 'UPDATE'
                ),
                has_function_privilege(
                    'bravo_shadow_runtime_test',
                    'pg_catalog.pg_advisory_xact_lock(bigint)', 'EXECUTE'
                )
        """).fetchone()
        assert privileges == (False, False, True)

    runtime_conninfo = psycopg.conninfo.conninfo_to_dict(postgres_database)
    runtime_conninfo["dbname"] = "bravo_shadow_test"
    runtime_conninfo["user"] = "bravo_shadow_runtime_test"
    runtime_conninfo["password"] = "bravo-shadow-test-only"

    # Autenticação independente: session_user e current_user são a própria
    # role runtime, sem SET ROLE a partir de uma sessão administrativa.
    with psycopg.connect(**runtime_conninfo) as connection:
        assert connection.execute(
            "SELECT session_user, current_user"
        ).fetchone() == (
            "bravo_shadow_runtime_test",
            "bravo_shadow_runtime_test",
        )

    runtime_store = PostgresReviewLedgerStore(
        lambda: psycopg.connect(**runtime_conninfo)
    )
    decision_id = register.pending[0].decision_id
    result = runtime_store.append(
        register,
        **_event_args(decision_id, f"runtime-role-{uuid4()}"),
    )
    assert len(result.history_for(decision_id)) == 1
    assert len(runtime_store.load(register).history_for(decision_id)) == 1
