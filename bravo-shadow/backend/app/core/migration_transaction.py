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


class MigrationTransactionError(RuntimeError):
    """Raised when a migration unit cannot obtain its transaction connection."""


def execute_migration_write_unit(
    unit_of_work_factory: Callable[[], PostgresUnitOfWork],
    operations: MigrationWriteOperations[DestinationT],
) -> DestinationT:
    """Run reserve, business insert, source map and success event atomically.

    PostgresUnitOfWork owns commit/rollback/close. If any callback raises,
    the context manager rolls the complete unit back. The caller must persist
    failure evidence separately after this transaction has been released.
    """
    with unit_of_work_factory() as unit:
        connection = unit.connection
        if connection is None:
            raise MigrationTransactionError("transaction_connection_unavailable")

        operations.reserve_batch(connection)
        destination = operations.write_business(connection)
        operations.write_source_map(connection, destination)
        operations.append_success_event(connection, destination)
        return destination
