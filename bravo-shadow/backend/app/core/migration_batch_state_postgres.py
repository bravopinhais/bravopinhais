"""PostgreSQL row-lock adapter for migration batch state transitions.

No connection is opened at import time. Callers must inject an approved
connection factory; this adapter only updates an already-created Shadow batch.
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from app.core.migration_batch_state import (
    BatchApproval,
    BatchState,
    BatchTransitionError,
    BatchStatus,
    transition_batch,
)
from app.core.postgres import PostgresUnitOfWork


class PostgresBatchStateStore:
    """Serialize transitions by locking the batch row inside one transaction."""

    def __init__(self, connection_factory: Callable[[], Any]) -> None:
        self._connection_factory = connection_factory

    @staticmethod
    def _execute(connection: Any, sql: str, params: tuple[Any, ...]) -> Any:
        cursor = connection.cursor()
        try:
            cursor.execute(sql, params)
            return cursor
        except Exception:
            cursor.close()
            raise

    @staticmethod
    def _timestamp(value: Any) -> str:
        if isinstance(value, datetime):
            return value.isoformat()
        return "" if value is None else str(value)

    def transition(
        self,
        batch_id: str,
        target: BatchStatus,
        *,
        approval: BatchApproval | None = None,
        expected_manifest_hash: str | None = None,
    ) -> BatchState:
        """Lock, validate and persist one transition atomically.

        This method does not create batches, authorize reviewer identities, or
        execute imports. Approval identity must be authenticated by its caller.
        """
        if not isinstance(batch_id, str) or not batch_id.strip():
            raise BatchTransitionError("batch_identity_required")

        with PostgresUnitOfWork(self._connection_factory) as uow:
            connection = uow.connection
            if connection is None:
                raise BatchTransitionError("transaction_connection_unavailable")

            cursor = self._execute(
                connection,
                """
                SELECT batch_id, manifest_hash, environment, status,
                       approved_by, approved_at, approved_manifest_hash
                FROM bravo_shadow.migration_batches
                WHERE batch_id = %s
                FOR UPDATE
                """,
                (batch_id,),
            )
            row = cursor.fetchone()
            cursor.close()
            if row is None:
                raise BatchTransitionError("batch_not_found")
            if len(row) != 7:
                raise BatchTransitionError("stored_batch_shape_invalid")

            stored_approval = None
            approval_values = row[4:7]
            if any(value is not None for value in approval_values):
                if not all(value is not None for value in approval_values):
                    raise BatchTransitionError("stored_approval_incomplete")
                stored_approval = BatchApproval(
                    reviewer_id=str(row[4]),
                    approved_at=self._timestamp(row[5]),
                    manifest_hash=str(row[6]),
                )

            current = BatchState(
                batch_id=str(row[0]),
                manifest_hash=str(row[1]),
                environment=str(row[2]),
                status=row[3],
                approval=stored_approval,
            )
            updated = transition_batch(
                current,
                target,
                approval=approval,
                expected_manifest_hash=expected_manifest_hash,
            )

            approved_by = updated.approval.reviewer_id if updated.approval else None
            approved_at = updated.approval.approved_at if updated.approval else None
            approved_hash = updated.approval.manifest_hash if updated.approval else None
            cursor = self._execute(
                connection,
                """
                UPDATE bravo_shadow.migration_batches
                SET status = %s,
                    approved_by = %s,
                    approved_at = %s,
                    approved_manifest_hash = %s,
                    finished_at = CASE
                        WHEN %s IN ('applied', 'verified', 'failed', 'rolled_back')
                        THEN now()
                        ELSE NULL
                    END
                WHERE batch_id = %s AND manifest_hash = %s AND status = %s
                RETURNING batch_id
                """,
                (
                    updated.status,
                    approved_by,
                    approved_at,
                    approved_hash,
                    updated.status,
                    batch_id,
                    current.manifest_hash,
                    current.status,
                ),
            )
            persisted = cursor.fetchone()
            cursor.close()
            if persisted is None:
                raise BatchTransitionError("concurrent_batch_transition")
            return updated
