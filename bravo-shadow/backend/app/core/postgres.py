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


class CommitSucceededCleanupError(RuntimeError):
    """O COMMIT foi confirmado, mas a conexão falhou ao ser encerrada."""


class PostgresUnitOfWork:
    """Gerencia commit/rollback/close de uma conexão por unidade de trabalho.

    A fábrica deve abrir uma conexão PostgreSQL nova. O driver concreto é
    injetado pelo ambiente, evitando conexão implícita ou fallback em memória.
    Se o commit falhar, tenta rollback para limpeza, mas não presume que isso
    desfaça um commit que o servidor talvez já tenha confirmado.
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
        commit_succeeded = False
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
                    commit_succeeded = True
                except BaseException as commit_error:
                    sqlstate = getattr(commit_error, "sqlstate", None)
                    server_confirmed_abort = (
                        isinstance(sqlstate, str)
                        and (
                            sqlstate.startswith("23")
                            or sqlstate.startswith("40")
                            or sqlstate.startswith("P0")
                        )
                    )
                    if server_confirmed_abort:
                        # O servidor respondeu com uma rejeição transacional
                        # explícita (integridade, rollback/serialização ou
                        # exceção PL/pgSQL). Não houve commit confirmado; a
                        # operação pode ser tentada novamente após corrigir a
                        # causa, sem classificar o resultado como desconhecido.
                        primary_error = commit_error
                        try:
                            connection.rollback()
                        except BaseException as rollback_error:
                            self._note_cleanup_failure(
                                primary_error, "rollback após rejeição do servidor",
                                rollback_error
                            )
                        raise

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
                if primary_error is None and commit_succeeded:
                    cleanup_error = CommitSucceededCleanupError(
                        "postgres_commit_succeeded_connection_close_failed"
                    )
                    primary_error = cleanup_error
                    self._note_cleanup_failure(
                        primary_error, "fechamento após commit confirmado", close_error
                    )
                    raise cleanup_error from close_error
                if primary_error is None:
                    raise
                self._note_cleanup_failure(
                    primary_error, "fechamento da conexão", close_error
                )
            finally:
                self.connection = None
        return False
