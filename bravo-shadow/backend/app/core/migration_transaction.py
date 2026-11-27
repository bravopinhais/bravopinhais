"""Atomic orchestration boundary for one migration write unit.

This module does not implement SQL or open connections. All persistence
callbacks receive the exact same connection owned by PostgresUnitOfWork.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, TypeVar

from app.core.postgres import PostgresUnitOfWork

DestinationT = TypeVar("DestinationT")


@dataclass(frozen=True, slots=True)
class MigrationWriteOperations(Generic[DestinationT]):
    """Persistence steps that a domain-specific PostgreSQL adapter must supply.

    reserve_batch must lock/check the batch and its approval/manifest binding.
    write_business inserts the domain row without silently overwriting.
    write_source_map records the source identity and destination link.
    append_success_event adds migration-specific success evidence, while
    append_audit_event writes the corresponding global audit_events record.
    Both use only the supplied connection and must not commit, rollback, or
    reconnect. This keeps business data, provenance and both event trails
    atomic; calling PostgresAuditSink.append() here would break that guarantee.
    """

    reserve_batch: Callable[[object], None]
    write_business: Callable[[object], DestinationT]
    write_source_map: Callable[[object, DestinationT], None]
    append_success_event: Callable[[object, DestinationT], None]
    append_audit_event: Callable[[object, DestinationT], None]
    append_failure_event: Callable[[BaseException], None]


class MigrationTransactionError(RuntimeError):
    """Raised when a migration unit cannot obtain its transaction connection."""


def execute_migration_write_unit(
    unit_of_work_factory: Callable[[], PostgresUnitOfWork],
    operations: MigrationWriteOperations[DestinationT],
) -> DestinationT:
    """Run the write unit atomically and record failures after rollback.

    The failure callback runs only after PostgresUnitOfWork has rolled back and
    released its connection. It must open its own transaction and record only
    metadata (batch/request IDs, stage and sanitized error code), never source
    payloads or credentials. If failure auditing also fails, the original
    migration exception remains primary and receives a diagnostic note.
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
    except BaseException as migration_error:
        try:
            operations.append_failure_event(migration_error)
        except BaseException as audit_error:
            add_note = getattr(migration_error, "add_note", None)
            if callable(add_note):
                add_note(
                    "Falha adicional ao persistir auditoria de falha: "
                    f"{type(audit_error).__name__}."
                )
        raise
