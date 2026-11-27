from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, TypeVar


class DbConnection(Protocol):
    """Subset de conexão DB-API necessário à unidade de trabalho."""

    def commit(self) -> None: ...
    def rollback(self) -> None: ...
    def close(self) -> None: ...


ConnectionT = TypeVar("ConnectionT", bound=DbConnection)


class CommitOutcomeUnknown(RuntimeError):
    """O servidor pode ter confirmado o COMMIT, mas a confirmação não chegou."""


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
            close = getattr(connection, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:
                    pass
            raise TypeError(
                "A connection_factory deve retornar uma conexão com commit, rollback e close chamáveis."
            )
        self.connection = connection
        return self

    @staticmethod
    def _note_cleanup_failure(primary_error: BaseException, operation: str, cleanup_error: BaseException) -> None:
        """Registra falha secundária sem substituir o erro que iniciou a limpeza."""
        add_note = getattr(primary_error, "add_note", None)
        if callable(add_note):
            add_note(
                f"Falha secundária durante {operation}: "
                f"{type(cleanup_error).__name__}."
            )

    def __exit__(self, exc_type, exc, traceback) -> bool:
        connection = self.connection
        if connection is None:
            return False

        primary_error = exc
        try:
            if exc_type is not None:
                try:
                    connection.rollback()
                except BaseException as rollback_error:
                    if primary_error is None:
                        primary_error = rollback_error
                        raise
                    self._note_cleanup_failure(
                        primary_error, "rollback", rollback_error
                    )
            else:
                try:
                    connection.commit()
                except BaseException as commit_error:
                    outcome_error = CommitOutcomeUnknown(
                        "postgres_commit_outcome_unknown"
                    )
                    primary_error = outcome_error
                    try:
                        connection.rollback()
                    except BaseException as rollback_error:
                        self._note_cleanup_failure(
                            primary_error, "rollback após resultado desconhecido do commit",
                            rollback_error
                        )
                    raise outcome_error from commit_error
        finally:
            try:
                connection.close()
            except BaseException as close_error:
                if primary_error is None:
                    raise
                self._note_cleanup_failure(
                    primary_error, "fechamento da conexão", close_error
                )
            finally:
                self.connection = None
        return False
