from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

from app.core.postgres_connection import create_postgres_connection_factory


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
