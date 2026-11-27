from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, TypeVar


class DbConnection(Protocol):
    """Subset de conexão DB-API necessário à unidade de trabalho."""

    def commit(self) -> None: ...
    def rollback(self) -> None: ...
    def close(self) -> None: ...


ConnectionT = TypeVar("ConnectionT", bound=DbConnection)


class PostgresUnitOfWork:
    """Gerencia commit/rollback/close de uma conexão por unidade de trabalho.

    A fábrica deve abrir uma conexão PostgreSQL nova. O driver concreto é
    injetado pelo ambiente, evitando conexão implícita ou fallback em memória.
    Se o próprio commit falhar, tenta rollback antes de liberar a conexão.
    """

    def __init__(self, connection_factory: Callable[[], ConnectionT]) -> None:
        if not callable(connection_factory):
            raise TypeError("connection_factory deve ser chamável.")
        self._connection_factory = connection_factory
        self.connection: ConnectionT | None = None

    def __enter__(self) -> PostgresUnitOfWork:
        connection = self._connection_factory()
        required_methods = ("commit", "rollback", "close")
        if any(not callable(getattr(connection, name, None)) for name in required_methods):
            raise TypeError(
                "A connection_factory deve retornar uma conexão com commit, rollback e close chamáveis."
            )
        self.connection = connection
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        connection = self.connection
        if connection is None:
            return False
        try:
            if exc_type is not None:
                connection.rollback()
            else:
                try:
                    connection.commit()
                except Exception:
                    connection.rollback()
                    raise
        finally:
            try:
                connection.close()
            finally:
                self.connection = None
        return False
