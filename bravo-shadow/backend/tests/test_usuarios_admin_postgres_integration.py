"""Integração real da alteração administrativa de usuários (PostgreSQL descartável)."""
from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from urllib.parse import urlparse
from uuid import uuid4

import psycopg
import pytest
from fastapi import HTTPException

from app.core.audit import AuditEvent
from app.core.postgres_audit import PostgresAuditSink
from app.core.postgres_usuarios import PostgresUsuariosRepository


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
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise RuntimeError("A URL de integração precisa usar PostgreSQL.")
    if parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError("Os testes só podem conectar a PostgreSQL local/descartável.")
    if database != "bravo_shadow_test":
        raise RuntimeError(
            "BRAVO_SHADOW_TEST_DATABASE_URL precisa apontar exatamente para "
            "o banco descartável bravo_shadow_test."
        )


@pytest.fixture
def postgres_users_database():
    if not DATABASE_URL:
        pytest.skip("PostgreSQL real não configurado; integração opt-in.")

    _guard_test_database(DATABASE_URL)
    docs = Path(__file__).resolve().parents[2] / "docs"
    users_ddl = docs / "sql-piloto-financeiro.sql"
    audit_ddl = docs / "sql-auditoria-rascunho.sql"

    with psycopg.connect(DATABASE_URL, autocommit=True) as connection:
        for role in ("anon", "authenticated", "service_role"):
            existing_role = connection.execute(
                "SELECT 1 FROM pg_roles WHERE rolname = %s", (role,)
            ).fetchone()
            if existing_role is None:
                connection.execute(f'CREATE ROLE "{role}" NOLOGIN')
        connection.execute("DROP SCHEMA IF EXISTS bravo_shadow CASCADE")
        connection.execute(users_ddl.read_text(encoding="utf-8"), prepare=False)
        connection.execute(audit_ddl.read_text(encoding="utf-8"), prepare=False)

    yield DATABASE_URL

    with psycopg.connect(DATABASE_URL, autocommit=True) as connection:
        connection.execute("DROP SCHEMA IF EXISTS bravo_shadow CASCADE")


def _insert_user(database_url: str, user_id: str, email: str, profile="Admin"):
    with psycopg.connect(database_url) as connection:
        connection.execute(
            """
            INSERT INTO bravo_shadow.usuarios
                (id, email, nome, loja, cargo, perfil, status)
            VALUES (%s, %s, %s, %s, %s, %s, 'Ativo')
            """,
            (user_id, email, "Usuário de teste", "Bravo", "Teste", profile),
        )


def _event(user_id: str) -> AuditEvent:
    return AuditEvent(
        actor_subject="google-integration-test",
        action="usuarios:update_administracao",
        entity_type="usuario",
        entity_id=user_id,
    )


def _repository(database_url: str) -> PostgresUsuariosRepository:
    return PostgresUsuariosRepository(lambda: psycopg.connect(database_url))


def _audit_sink(database_url: str) -> PostgresAuditSink:
    return PostgresAuditSink(lambda: psycopg.connect(database_url))


def test_real_postgres_updates_profile_and_audit_atomically(postgres_users_database):
    database_url = postgres_users_database
    _insert_user(database_url, "usr_target", "target@example.test")
    _insert_user(database_url, "usr_other", "other@example.test")

    _repository(database_url).update_administrative_state(
        "usr_target",
        perfil="Operador",
        status="Ativo",
        event=_event("usr_target"),
        audit_sink=_audit_sink(database_url),
    )

    with psycopg.connect(database_url) as connection:
        user = connection.execute(
            "SELECT perfil, status, version FROM bravo_shadow.usuarios WHERE id = %s",
            ("usr_target",),
        ).fetchone()
        audit = connection.execute(
            """
            SELECT actor_subject, action, entity_type, entity_id, outcome
            FROM bravo_shadow.audit_events WHERE entity_id = %s
            """,
            ("usr_target",),
        ).fetchone()

    assert user == ("Operador", "Ativo", 2)
    assert audit == (
        "google-integration-test",
        "usuarios:update_administracao",
        "usuario",
        "usr_target",
        "success",
    )


def test_real_postgres_rejects_removing_last_active_admin(postgres_users_database):
    database_url = postgres_users_database
    _insert_user(database_url, "usr_last_admin", "last@example.test")

    with pytest.raises(HTTPException) as error:
        _repository(database_url).update_administrative_state(
            "usr_last_admin",
            perfil="Operador",
            status="Ativo",
            event=_event("usr_last_admin"),
            audit_sink=_audit_sink(database_url),
        )

    assert error.value.status_code == 409
    with psycopg.connect(database_url) as connection:
        user = connection.execute(
            "SELECT perfil, status, version FROM bravo_shadow.usuarios WHERE id = %s",
            ("usr_last_admin",),
        ).fetchone()
        audit_count = connection.execute(
            "SELECT count(*) FROM bravo_shadow.audit_events"
        ).fetchone()[0]

    assert user == ("Admin", "Ativo", 1)
    assert audit_count == 0


def test_real_postgres_audit_failure_rolls_back_user_change(postgres_users_database):
    database_url = postgres_users_database
    _insert_user(database_url, "usr_rollback", "rollback@example.test")
    # Mantém outro Admin ativo para que a falha exercite a auditoria,
    # e não a proteção independente do último administrador.
    _insert_user(database_url, "usr_rollback_peer", "rollback-peer@example.test")

    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute(
            """
            CREATE FUNCTION bravo_shadow.reject_admin_audit() RETURNS trigger
            LANGUAGE plpgsql AS $$
            BEGIN
                RAISE EXCEPTION 'forced audit failure';
            END;
            $$
            """
        )
        connection.execute(
            """
            CREATE TRIGGER reject_admin_audit_before_insert
            BEFORE INSERT ON bravo_shadow.audit_events
            FOR EACH ROW EXECUTE FUNCTION bravo_shadow.reject_admin_audit()
            """
        )

    try:
        with pytest.raises(psycopg.Error, match="forced audit failure"):
            _repository(database_url).update_administrative_state(
                "usr_rollback",
                perfil="Operador",
                status="Ativo",
                event=_event("usr_rollback"),
                audit_sink=_audit_sink(database_url),
            )

        with psycopg.connect(database_url) as connection:
            user = connection.execute(
                "SELECT perfil, status, version FROM bravo_shadow.usuarios WHERE id = %s",
                ("usr_rollback",),
            ).fetchone()
            audit_count = connection.execute(
                "SELECT count(*) FROM bravo_shadow.audit_events"
            ).fetchone()[0]
        assert user == ("Admin", "Ativo", 1)
        assert audit_count == 0
    finally:
        with psycopg.connect(database_url, autocommit=True) as connection:
            connection.execute(
                "DROP TRIGGER IF EXISTS reject_admin_audit_before_insert "
                "ON bravo_shadow.audit_events"
            )
            connection.execute(
                "DROP FUNCTION IF EXISTS bravo_shadow.reject_admin_audit()"
            )


def test_real_postgres_concurrent_demotions_preserve_one_active_admin(postgres_users_database):
    database_url = postgres_users_database
    _insert_user(database_url, "usr_admin_a", "admin-a@example.test")
    _insert_user(database_url, "usr_admin_b", "admin-b@example.test")
    barrier = Barrier(2)

    def demote(user_id: str):
        barrier.wait(timeout=10)
        try:
            _repository(database_url).update_administrative_state(
                user_id,
                perfil="Operador",
                status="Ativo",
                event=_event(user_id),
                audit_sink=_audit_sink(database_url),
            )
            return "committed"
        except HTTPException as error:
            if error.status_code != 409:
                raise
            return "last_admin_guard"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(
            pool.map(demote, ("usr_admin_a", "usr_admin_b"))
        )

    assert outcomes.count("committed") == 1
    assert outcomes.count("last_admin_guard") == 1

    with psycopg.connect(database_url) as connection:
        remaining_admins = connection.execute(
            "SELECT count(*) FROM bravo_shadow.usuarios "
            "WHERE perfil = 'Admin' AND status = 'Ativo'"
        ).fetchone()[0]
        audit_count = connection.execute(
            "SELECT count(*) FROM bravo_shadow.audit_events"
        ).fetchone()[0]

    assert remaining_admins == 1
    assert audit_count == 1



def _deactivation_event(user_id: str) -> AuditEvent:
    return AuditEvent(
        actor_subject="google-integration-test",
        action="usuarios:desativar",
        entity_type="usuario",
        entity_id=user_id,
    )


def test_real_postgres_deactivates_without_deleting_and_audits_atomically(postgres_users_database):
    database_url = postgres_users_database
    _insert_user(database_url, "usr_to_deactivate", "deactivate@example.test")
    _insert_user(database_url, "usr_other_admin", "other-admin@example.test")

    _repository(database_url).deactivate_user(
        "usr_to_deactivate",
        event=_deactivation_event("usr_to_deactivate"),
        audit_sink=_audit_sink(database_url),
    )

    with psycopg.connect(database_url) as connection:
        user_row = connection.execute(
            "SELECT id, perfil, status, version FROM bravo_shadow.usuarios WHERE id = %s",
            ("usr_to_deactivate",),
        ).fetchone()
        audit = connection.execute(
            "SELECT actor_subject, action, entity_type, entity_id, outcome "
            "FROM bravo_shadow.audit_events WHERE entity_id = %s",
            ("usr_to_deactivate",),
        ).fetchone()

    assert user_row == ("usr_to_deactivate", "Admin", "Inativo", 2)
    assert audit == (
        "google-integration-test",
        "usuarios:desativar",
        "usuario",
        "usr_to_deactivate",
        "success",
    )


def test_real_postgres_refuses_to_deactivate_last_admin(postgres_users_database):
    database_url = postgres_users_database
    _insert_user(database_url, "usr_only_admin", "only-admin@example.test")

    with pytest.raises(HTTPException) as error:
        _repository(database_url).deactivate_user(
            "usr_only_admin",
            event=_deactivation_event("usr_only_admin"),
            audit_sink=_audit_sink(database_url),
        )

    assert error.value.status_code == 409
    with psycopg.connect(database_url) as connection:
        user_row = connection.execute(
            "SELECT perfil, status, version FROM bravo_shadow.usuarios WHERE id = %s",
            ("usr_only_admin",),
        ).fetchone()
        audit_count = connection.execute(
            "SELECT count(*) FROM bravo_shadow.audit_events"
        ).fetchone()[0]

    assert user_row == ("Admin", "Ativo", 1)
    assert audit_count == 0


def test_real_postgres_deactivation_audit_failure_rolls_back_status(postgres_users_database):
    database_url = postgres_users_database
    _insert_user(database_url, "usr_deactivate_rollback", "deactivate-rollback@example.test")
    _insert_user(database_url, "usr_deactivate_peer", "deactivate-peer@example.test")

    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute(
            """
            CREATE FUNCTION bravo_shadow.reject_deactivation_audit() RETURNS trigger
            LANGUAGE plpgsql AS $$
            BEGIN
                RAISE EXCEPTION 'forced deactivation audit failure';
            END;
            $$
            """
        )
        connection.execute(
            """
            CREATE TRIGGER reject_deactivation_audit_before_insert
            BEFORE INSERT ON bravo_shadow.audit_events
            FOR EACH ROW EXECUTE FUNCTION bravo_shadow.reject_deactivation_audit()
            """
        )

    try:
        with pytest.raises(psycopg.Error, match="forced deactivation audit failure"):
            _repository(database_url).deactivate_user(
                "usr_deactivate_rollback",
                event=_deactivation_event("usr_deactivate_rollback"),
                audit_sink=_audit_sink(database_url),
            )

        with psycopg.connect(database_url) as connection:
            user_row = connection.execute(
                "SELECT status, version FROM bravo_shadow.usuarios WHERE id = %s",
                ("usr_deactivate_rollback",),
            ).fetchone()
            audit_count = connection.execute(
                "SELECT count(*) FROM bravo_shadow.audit_events"
            ).fetchone()[0]
        assert user_row == ("Ativo", 1)
        assert audit_count == 0
    finally:
        with psycopg.connect(database_url, autocommit=True) as connection:
            connection.execute(
                "DROP TRIGGER IF EXISTS reject_deactivation_audit_before_insert "
                "ON bravo_shadow.audit_events"
            )
            connection.execute(
                "DROP FUNCTION IF EXISTS bravo_shadow.reject_deactivation_audit()"
            )

def test_real_postgres_concurrent_deactivations_preserve_one_active_admin(postgres_users_database):
    database_url = postgres_users_database
    _insert_user(database_url, "usr_deactivate_admin_a", "deactivate-admin-a@example.test")
    _insert_user(database_url, "usr_deactivate_admin_b", "deactivate-admin-b@example.test")
    barrier = Barrier(2)

    def deactivate(user_id: str):
        barrier.wait(timeout=10)
        try:
            _repository(database_url).deactivate_user(
                user_id,
                event=_deactivation_event(user_id),
                audit_sink=_audit_sink(database_url),
            )
            return "committed"
        except HTTPException as error:
            if error.status_code != 409:
                raise
            return "last_admin_guard"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(
            pool.map(
                deactivate,
                ("usr_deactivate_admin_a", "usr_deactivate_admin_b"),
            )
        )

    assert outcomes.count("committed") == 1
    assert outcomes.count("last_admin_guard") == 1

    with psycopg.connect(database_url) as connection:
        remaining_admins = connection.execute(
            "SELECT count(*) FROM bravo_shadow.usuarios "
            "WHERE perfil = 'Admin' AND status = 'Ativo'"
        ).fetchone()[0]
        inactive_admins = connection.execute(
            "SELECT count(*) FROM bravo_shadow.usuarios "
            "WHERE perfil = 'Admin' AND status = 'Inativo'"
        ).fetchone()[0]
        audit_count = connection.execute(
            "SELECT count(*) FROM bravo_shadow.audit_events "
            "WHERE action = 'usuarios:desativar'"
        ).fetchone()[0]

    assert remaining_admins == 1
    assert inactive_admins == 1
    assert audit_count == 1


def test_real_postgres_cadastral_update_cannot_restore_stale_admin_state(postgres_users_database):
    database_url = postgres_users_database
    _insert_user(database_url, "usr_cadastral_race", "cadastral-race@example.com")
    # Mantém outro Admin ativo para que o teste possa rebaixar o usuário-alvo.
    _insert_user(database_url, "usr_cadastral_race_guard", "cadastral-guard@example.com")

    repository = _repository(database_url)
    # Simula uma leitura cadastral antiga anterior à mudança administrativa.
    stale_snapshot = repository.get("usr_cadastral_race")
    assert stale_snapshot.perfil == "Admin"
    assert stale_snapshot.status == "Ativo"

    repository.update_administrative_state(
        "usr_cadastral_race",
        perfil="Operador",
        status="Ativo",
        event=_event("usr_cadastral_race"),
        audit_sink=_audit_sink(database_url),
    )
    from app.modules.usuarios.schemas import UsuarioDadosCadastraisUpdateInput
    from app.modules.usuarios.service import UsuariosService

    service = UsuariosService(repository=repository)
    # Simula a leitura antiga que ocorreria antes da alteração administrativa.
    # O adapter PostgreSQL deve evitar usar esse snapshot na escrita cadastral.
    service.get = lambda _item_id: stale_snapshot
    service.update_cadastral(
        "usr_cadastral_race",
        UsuarioDadosCadastraisUpdateInput(nome="Nome cadastral atualizado"),
    )

    with psycopg.connect(database_url) as connection:
        row = connection.execute(
            "SELECT nome, perfil, status, version FROM bravo_shadow.usuarios WHERE id = %s",
            ("usr_cadastral_race",),
        ).fetchone()

    assert row == ("Nome cadastral atualizado", "Operador", "Ativo", 3)



def test_real_postgres_mixed_concurrent_demotion_and_deactivation_preserve_admin(
    postgres_users_database,
):
    """As duas operações compartilham a mesma serialização do último Admin."""
    database_url = postgres_users_database
    _insert_user(database_url, "usr_mixed_admin_a", "mixed-admin-a@example.test")
    _insert_user(database_url, "usr_mixed_admin_b", "mixed-admin-b@example.test")
    barrier = Barrier(2)

    def demote():
        barrier.wait(timeout=10)
        try:
            _repository(database_url).update_administrative_state(
                "usr_mixed_admin_a",
                perfil="Operador",
                status="Ativo",
                event=_event("usr_mixed_admin_a"),
                audit_sink=_audit_sink(database_url),
            )
            return "committed"
        except HTTPException as error:
            if error.status_code != 409:
                raise
            return "last_admin_guard"

    def deactivate():
        barrier.wait(timeout=10)
        try:
            _repository(database_url).deactivate_user(
                "usr_mixed_admin_b",
                event=_deactivation_event("usr_mixed_admin_b"),
                audit_sink=_audit_sink(database_url),
            )
            return "committed"
        except HTTPException as error:
            if error.status_code != 409:
                raise
            return "last_admin_guard"

    with ThreadPoolExecutor(max_workers=2) as pool:
        demotion = pool.submit(demote)
        deactivation = pool.submit(deactivate)
        outcomes = [demotion.result(timeout=20), deactivation.result(timeout=20)]

    assert outcomes.count("committed") == 1
    assert outcomes.count("last_admin_guard") == 1

    with psycopg.connect(database_url) as connection:
        active_admins = connection.execute(
            "SELECT count(*) FROM bravo_shadow.usuarios "
            "WHERE perfil = 'Admin' AND status = 'Ativo'"
        ).fetchone()[0]
        audit_count = connection.execute(
            "SELECT count(*) FROM bravo_shadow.audit_events"
        ).fetchone()[0]

    assert active_admins == 1
    assert audit_count == 1


def test_real_postgres_concurrent_cadastral_update_and_demotion_do_not_restore_privileges(
    postgres_users_database,
):
    """UPDATE cadastral e alteração privilegiada podem concorrer sem lost update."""
    from app.modules.usuarios.schemas import UsuarioDadosCadastraisUpdateInput

    database_url = postgres_users_database
    _insert_user(database_url, "usr_cadastral_concurrent", "cadastral-concurrent@example.test")
    _insert_user(
        database_url,
        "usr_cadastral_concurrent_guard",
        "cadastral-concurrent-guard@example.test",
    )
    repository = _repository(database_url)
    barrier = Barrier(2)

    def update_cadastral():
        barrier.wait(timeout=10)
        return repository.update_cadastral(
            "usr_cadastral_concurrent",
            nome="Nome cadastral concorrente",
        )

    def demote():
        barrier.wait(timeout=10)
        return repository.update_administrative_state(
            "usr_cadastral_concurrent",
            perfil="Operador",
            status="Ativo",
            event=_event("usr_cadastral_concurrent"),
            audit_sink=_audit_sink(database_url),
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        cadastral = pool.submit(update_cadastral)
        administrative = pool.submit(demote)
        cadastral.result(timeout=20)
        administrative.result(timeout=20)

    with psycopg.connect(database_url) as connection:
        row = connection.execute(
            "SELECT nome, perfil, status, version FROM bravo_shadow.usuarios "
            "WHERE id = %s",
            ("usr_cadastral_concurrent",),
        ).fetchone()
        active_admins = connection.execute(
            "SELECT count(*) FROM bravo_shadow.usuarios "
            "WHERE perfil = 'Admin' AND status = 'Ativo'"
        ).fetchone()[0]
        audit_count = connection.execute(
            "SELECT count(*) FROM bravo_shadow.audit_events"
        ).fetchone()[0]

    assert row == ("Nome cadastral concorrente", "Operador", "Ativo", 3)
    assert active_admins == 1
    assert audit_count == 1


@pytest.mark.parametrize("role", ["anon", "authenticated", "service_role"])
def test_real_postgres_client_roles_cannot_access_users_without_explicit_grants(
    postgres_users_database,
    role,
):
    """Confirma que os papéis de API permanecem fechados no SQL ainda não habilitado."""
    database_url = postgres_users_database

    with psycopg.connect(database_url) as connection:
        connection.execute(f'SET ROLE "{role}"')
        can_use_schema = connection.execute(
            "SELECT has_schema_privilege(current_user, 'bravo_shadow', 'USAGE')"
        ).fetchone()[0]
        assert can_use_schema is False

        with pytest.raises(psycopg.errors.InsufficientPrivilege) as error:
            connection.execute("SELECT id FROM bravo_shadow.usuarios LIMIT 1")
        assert error.value.sqlstate == "42501"
