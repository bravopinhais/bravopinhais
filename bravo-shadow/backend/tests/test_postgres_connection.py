from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

from app.core.postgres_connection import (
    create_migration_postgres_connection_factory,
    create_postgres_connection_factory,
)


def test_requires_database_url(monkeypatch):
    monkeypatch.delenv("BRAVO_DATABASE_URL", raising=False)
    with pytest.raises(ValueError, match="BRAVO_DATABASE_URL"):
        create_postgres_connection_factory()


def test_rejects_non_postgres_url():
    with pytest.raises(ValueError, match="URL PostgreSQL"):
        create_postgres_connection_factory("https://example.invalid")


def test_factory_opens_connection_only_when_called(monkeypatch):
    calls = []
    sentinel = object()

    def fake_connect(conninfo, **kwargs):
        calls.append((conninfo, kwargs))
        return sentinel

    monkeypatch.setitem(sys.modules, "psycopg", SimpleNamespace(connect=fake_connect))
    factory = create_postgres_connection_factory(
        "postgresql://bravo_shadow:local-only@127.0.0.1:54322/postgres"
    )

    assert calls == []
    assert factory() is sentinel
    assert calls == [
        (
            "postgresql://bravo_shadow:local-only@127.0.0.1:54322/postgres",
            {"connect_timeout": 5, "application_name": "bravo-shadow-api"},
        )
    ]



def test_migration_factory_requires_its_own_environment_variable(monkeypatch):
    monkeypatch.delenv("BRAVO_MIGRATION_DATABASE_URL", raising=False)
    monkeypatch.setenv(
        "BRAVO_DATABASE_URL",
        "postgresql://runtime:runtime@127.0.0.1:54322/postgres",
    )
    with pytest.raises(ValueError, match="BRAVO_MIGRATION_DATABASE_URL"):
        create_migration_postgres_connection_factory()


def test_migration_factory_rejects_runtime_credential_reuse(monkeypatch):
    shared = "postgresql://same-role:secret@127.0.0.1:54322/postgres"
    monkeypatch.setenv("BRAVO_DATABASE_URL", shared)
    with pytest.raises(ValueError, match="diferente da credencial runtime"):
        create_migration_postgres_connection_factory(shared)


def test_migration_factory_is_lazy_and_uses_distinct_application_name(monkeypatch):
    calls = []
    sentinel = object()
    migration_url = "postgresql://migrator:local-only@127.0.0.1:54322/postgres"

    def fake_connect(conninfo, **kwargs):
        calls.append((conninfo, kwargs))
        return sentinel

    monkeypatch.setenv("BRAVO_MIGRATION_DATABASE_URL", migration_url)
    monkeypatch.setenv(
        "BRAVO_DATABASE_URL",
        "postgresql://runtime:local-only@127.0.0.1:54322/postgres",
    )
    monkeypatch.setitem(sys.modules, "psycopg", SimpleNamespace(connect=fake_connect))

    factory = create_migration_postgres_connection_factory()
    assert calls == []
    assert factory() is sentinel
    assert calls == [
        (
            migration_url,
            {
                "connect_timeout": 5,
                "application_name": "bravo-shadow-migration-preparation",
            },
        )
    ]
