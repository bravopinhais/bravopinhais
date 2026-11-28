from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any


def create_postgres_connection_factory(
    database_url: str | None = None,
) -> Callable[[], Any]:
    """Cria uma fábrica DB-API Psycopg sem abrir conexão durante o startup.

    A URL é lida somente no backend. Nenhuma credencial é embutida no código
    ou enviada ao frontend. Cada chamada da fábrica abre uma conexão nova.
    """
    conninfo = (database_url or os.getenv("BRAVO_DATABASE_URL", "")).strip()
    if not conninfo:
        raise ValueError(
            "BRAVO_DATABASE_URL é obrigatória quando BRAVO_STORAGE_BACKEND=postgres."
        )
    if not conninfo.startswith(("postgresql://", "postgres://")):
        raise ValueError(
            "BRAVO_DATABASE_URL deve usar uma URL PostgreSQL (postgresql://)."
        )

    try:
        from psycopg import connect
    except ImportError as exc:
        raise RuntimeError(
            "O driver Psycopg não está instalado. Instale backend/requirements.txt."
        ) from exc

    def connect_once():
        return connect(
            conninfo,
            connect_timeout=5,
            application_name="bravo-shadow-api",
        )

    return connect_once


def create_migration_postgres_connection_factory(
    database_url: str | None = None,
) -> Callable[[], Any]:
    """Cria conexão exclusiva de preparação, sem fallback para a URL runtime.

    A credencial deve existir somente no ambiente controlado de preparação.
    Esta função não é importada nem chamada pelo startup da API.
    """
    conninfo = (
        database_url
        if database_url is not None
        else os.getenv("BRAVO_MIGRATION_DATABASE_URL", "")
    ).strip()
    if not conninfo:
        raise ValueError(
            "BRAVO_MIGRATION_DATABASE_URL é obrigatória para preparação controlada."
        )
    if not conninfo.startswith(("postgresql://", "postgres://")):
        raise ValueError(
            "BRAVO_MIGRATION_DATABASE_URL deve usar uma URL PostgreSQL (postgresql://)."
        )

    runtime_conninfo = os.getenv("BRAVO_DATABASE_URL", "").strip()
    if runtime_conninfo and conninfo == runtime_conninfo:
        raise ValueError(
            "A credencial de preparação deve ser diferente da credencial runtime."
        )

    try:
        from psycopg import connect
    except ImportError as exc:
        raise RuntimeError(
            "O driver Psycopg não está instalado. Instale backend/requirements.txt."
        ) from exc

    def connect_once():
        return connect(
            conninfo,
            connect_timeout=5,
            application_name="bravo-shadow-migration-preparation",
        )

    return connect_once

