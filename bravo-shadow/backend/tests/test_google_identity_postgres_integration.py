"""Contratos PostgreSQL do vínculo Google em banco descartável, com dados sintéticos."""
from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from urllib.parse import urlparse
from uuid import uuid4

import psycopg
import pytest


DATABASE_URL = os.getenv("BRAVO_SHADOW_TEST_DATABASE_URL")
ISSUER = "https://accounts.google.com"


def _guard_test_database(url: str) -> None:
    if os.getenv("BRAVO_SHADOW_ALLOW_DESTRUCTIVE_TEST_DATABASE") != "1":
        raise RuntimeError("Integração destrutiva bloqueada fora do banco descartável.")
    parsed = urlparse(url)
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise RuntimeError("A integração exige PostgreSQL.")
    if parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError("A integração aceita somente PostgreSQL local/descartável.")
    if parsed.path.lstrip("/") != "bravo_shadow_test":
        raise RuntimeError("Banco incorreto: esperado bravo_shadow_test.")


@pytest.fixture
def google_identity_database():
    if not DATABASE_URL:
        pytest.skip("PostgreSQL descartável não configurado.")
    _guard_test_database(DATABASE_URL)
    migration_dir = Path(__file__).resolve().parents[2] / "supabase" / "migrations"
    migrations = sorted(migration_dir.glob("*.sql"))
    if len(migrations) != 7:
        raise RuntimeError(f"Esperadas 7 migrations; encontradas {len(migrations)}.")
    with psycopg.connect(DATABASE_URL, autocommit=True) as connection:
        for role in ("anon", "authenticated", "service_role"):
            if connection.execute(
                "SELECT 1 FROM pg_roles WHERE rolname = %s", (role,)
            ).fetchone() is None:
                connection.execute(f'CREATE ROLE "{role}" NOLOGIN')
        connection.execute("DROP SCHEMA IF EXISTS bravo_shadow CASCADE")
        for migration in migrations:
            connection.execute(migration.read_text(encoding="utf-8"), prepare=False)
    try:
        yield DATABASE_URL
    finally:
        with psycopg.connect(DATABASE_URL, autocommit=True) as connection:
            connection.execute("DROP SCHEMA IF EXISTS bravo_shadow CASCADE")


def _insert_user(connection, user_id: str) -> None:
    connection.execute(
        """
        INSERT INTO bravo_shadow.usuarios (id, email, nome, cargo, perfil, status)
        VALUES (%s, %s, %s, 'Operador', 'Operador', 'Ativo')
        """,
        (user_id, f"{user_id}@example.invalid", "Usuário sintético"),
    )


def _insert_identity(connection, user_id: str, subject: str) -> None:
    connection.execute(
        """
        INSERT INTO bravo_shadow.google_identities
            (user_id, issuer, subject, verified_email_at_link, linked_by)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (user_id, ISSUER, subject, f"{user_id}@example.invalid", "admin-sintetico"),
    )


def test_google_identity_requires_existing_bravo_user(google_identity_database):
    with psycopg.connect(google_identity_database) as connection:
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            _insert_identity(connection, "usuario-inexistente", "sub-inexistente")


@pytest.mark.parametrize(
    ("issuer", "subject", "verified_email", "linked_by"),
    [
        ("https://issuer.invalid", "sub-1", "teste@example.invalid", "admin"),
        (ISSUER, "   ", "teste@example.invalid", "admin"),
        (ISSUER, "sub-1", "  ", "admin"),
        (ISSUER, "sub-1", "teste@example.invalid", " "),
    ],
)
def test_google_identity_rejects_invalid_identity_fields(
    google_identity_database, issuer, subject, verified_email, linked_by
):
    user_id = f"user-{uuid4().hex}"
    with psycopg.connect(google_identity_database) as connection:
        _insert_user(connection, user_id)
        with pytest.raises(psycopg.errors.CheckViolation):
            connection.execute(
                """
                INSERT INTO bravo_shadow.google_identities
                    (user_id, issuer, subject, verified_email_at_link, linked_by)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (user_id, issuer, subject, verified_email, linked_by),
            )


def test_google_identity_enforces_one_identity_per_user_and_unique_google_subject(
    google_identity_database,
):
    with psycopg.connect(google_identity_database) as connection:
        user_a, user_b = f"user-{uuid4().hex}", f"user-{uuid4().hex}"
        _insert_user(connection, user_a)
        _insert_user(connection, user_b)
        _insert_identity(connection, user_a, f"sub-{uuid4().hex}")

        with pytest.raises(psycopg.errors.UniqueViolation):
            _insert_identity(connection, user_a, f"sub-{uuid4().hex}")

        user_c = f"user-{uuid4().hex}"
        _insert_user(connection, user_c)
        subject = f"sub-{uuid4().hex}"
        _insert_identity(connection, user_b, subject)
        with pytest.raises(psycopg.errors.UniqueViolation):
            _insert_identity(connection, user_c, subject)


def test_google_identity_unique_constraint_is_safe_under_concurrency(
    google_identity_database,
):
    user_a, user_b = f"user-{uuid4().hex}", f"user-{uuid4().hex}"
    subject = f"sub-{uuid4().hex}"
    with psycopg.connect(google_identity_database) as connection:
        _insert_user(connection, user_a)
        _insert_user(connection, user_b)

    barrier = Barrier(2)

    def attempt(user_id: str) -> str:
        barrier.wait(timeout=10)
        try:
            with psycopg.connect(google_identity_database) as connection:
                _insert_identity(connection, user_id, subject)
            return "committed"
        except psycopg.errors.UniqueViolation:
            return "duplicate_rejected"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(attempt, (user_a, user_b)))

    assert outcomes.count("committed") == 1
    assert outcomes.count("duplicate_rejected") == 1
    with psycopg.connect(google_identity_database) as connection:
        count = connection.execute(
            "SELECT count(*) FROM bravo_shadow.google_identities WHERE issuer = %s AND subject = %s",
            (ISSUER, subject),
        ).fetchone()[0]
    assert count == 1


def test_google_identity_is_forced_rls_and_has_no_client_role_grants(
    google_identity_database,
):
    with psycopg.connect(google_identity_database) as connection:
        rls = connection.execute(
            """
            SELECT c.relrowsecurity, c.relforcerowsecurity
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'bravo_shadow'
              AND c.relname = 'google_identities'
            """
        ).fetchone()
        assert rls == (True, True)

        for role in ("anon", "authenticated", "service_role"):
            privileges = connection.execute(
                """
                SELECT
                    has_table_privilege(%s, 'bravo_shadow.google_identities', 'SELECT'),
                    has_table_privilege(%s, 'bravo_shadow.google_identities', 'INSERT'),
                    has_table_privilege(%s, 'bravo_shadow.google_identities', 'UPDATE'),
                    has_table_privilege(%s, 'bravo_shadow.google_identities', 'DELETE')
                """,
                (role, role, role, role),
            ).fetchone()
            assert privileges == (False, False, False, False), (role, privileges)
