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
from app.core.migration_review import ReviewValidationError
from app.core.migration_review_postgres import PostgresReviewLedgerStore
from test_migration_decisions import setup_batch


DATABASE_URL = os.getenv("BRAVO_SHADOW_TEST_DATABASE_URL")


def _guard_test_database(url: str) -> None:
    parsed = urlparse(url)
    database = parsed.path.lstrip("/")
    if not database.endswith("_test"):
        raise RuntimeError(
            "BRAVO_SHADOW_TEST_DATABASE_URL precisa apontar para um banco "
            "descartável cujo nome termine em _test."
        )
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise RuntimeError("A URL de integração precisa usar PostgreSQL.")


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
        connection.execute(schema_sql.read_text(encoding="utf-8"), prepare=False)

    yield DATABASE_URL

    with psycopg.connect(DATABASE_URL, autocommit=True) as connection:
        connection.execute("DROP SCHEMA IF EXISTS bravo_shadow CASCADE")


def _register():
    _, _, preflight, manifest = setup_batch()
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
