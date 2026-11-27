"""Atomic orchestration boundary for one migration write unit.

This module does not implement SQL or open connections. All persistence
callbacks receive the exact same connection owned by PostgresUnitOfWork.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, TypeVar

from app.core.postgres import (
    CommitOutcomeUnknown,
    CommitSucceededCleanupError,
    PostgresUnitOfWork,
)

DestinationT = TypeVar("DestinationT")


@dataclass(frozen=True, slots=True)
class MigrationWriteOperations(Generic[DestinationT]):
    """Persistence steps supplied by a domain-specific PostgreSQL adapter.

    The success callbacks use the same transaction connection. Failure and
    unknown-outcome callbacks run only after that connection is closed and
    must persist sanitized metadata in a separate transaction. An unknown
    COMMIT callback must atomically quarantine the batch as needs_review and
    append its evidence event; it must never retry the batch. A cleanup error
    after a confirmed COMMIT is audited separately and is not a failed write.
    """

    reserve_batch: Callable[[object], None]
    write_business: Callable[[object], DestinationT]
    write_source_map: Callable[[object, DestinationT], None]
    append_success_event: Callable[[object, DestinationT], None]
    append_audit_event: Callable[[object, DestinationT], None]
    append_failure_event: Callable[[BaseException], None]
    append_unknown_outcome_event: Callable[[CommitOutcomeUnknown], None]
    append_committed_cleanup_event: Callable[[CommitSucceededCleanupError], None]


class MigrationTransactionError(RuntimeError):
    """Raised when a migration unit cannot obtain its transaction connection."""


def _add_secondary_note(primary_error: BaseException, label: str, secondary: BaseException) -> None:
    add_note = getattr(primary_error, "add_note", None)
    if callable(add_note):
        add_note(f"{label}: {type(secondary).__name__}.")


def execute_migration_write_unit(
    unit_of_work_factory: Callable[[], PostgresUnitOfWork],
    operations: MigrationWriteOperations[DestinationT],
) -> DestinationT:
    """Run one atomic write and classify transaction outcomes conservatively.

    A failure before COMMIT is recorded only after rollback/connection cleanup.
    A COMMIT exception is different: PostgreSQL may have committed even when
    the client did not receive the acknowledgement. Such cases are recorded
    as outcome-unknown and must be quarantined/reconciled; they are never
    reported as confirmed failures or retried automatically.
    """
    try:
        with unit_of_work_factory() as unit:
            connection = unit.connection
            if connection is None:
                raise MigrationTransactionError("transaction_connection_unavailable")

            operations.reserve_batch(connection)
            destination = operations.write_business(connection)
            operations.write_source_map(connection, destination)
            operations.append_success_event(connection, destination)
            operations.append_audit_event(connection, destination)
            return destination
    except CommitSucceededCleanupError as cleanup_error:
        try:
            operations.append_committed_cleanup_event(cleanup_error)
        except BaseException as audit_error:
            _add_secondary_note(
                cleanup_error,
                "Falha adicional ao registrar limpeza após COMMIT confirmado",
                audit_error,
            )
        raise
    except CommitOutcomeUnknown as unknown_error:
        try:
            operations.append_unknown_outcome_event(unknown_error)
        except BaseException as audit_error:
            _add_secondary_note(
                unknown_error,
                "Falha adicional ao registrar resultado desconhecido do COMMIT",
                audit_error,
            )
        raise
    except BaseException as migration_error:
        try:
            operations.append_failure_event(migration_error)
        except BaseException as audit_error:
            _add_secondary_note(
                migration_error,
                "Falha adicional ao persistir auditoria de falha",
                audit_error,
            )
        raise
