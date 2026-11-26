"""PostgreSQL adapter for append-only migration review history.

Shadow-only. The adapter uses an injected DB-API connection factory; importing
this module never opens a connection. The SQL schema remains a reviewed draft
until roles, RLS policies and local migrations are explicitly approved.
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from app.core.migration_decisions import DecisionRegister
from app.core.migration_review import (
    ReviewChoice,
    ReviewLedger,
    ReviewValidationError,
    ReviewEvent,
    append_review,
    verify_review_ledger,
)
from app.core.postgres import PostgresUnitOfWork


class PostgresReviewLedgerStore:
    """Durable review ledger with explicit snapshot initialization.

    initialize is the only operation that creates the batch and decision
    snapshot. load never creates data. append locks one decision row, checks
    the persisted manifest and version, and inserts one immutable event
    in the same transaction.
    """

    def __init__(self, connection_factory: Callable[[], Any]) -> None:
        self._connection_factory = connection_factory

    @staticmethod
    def _run(connection: Any, sql: str, params: tuple[Any, ...] = ()) -> Any:
        cursor = connection.cursor()
        try:
            cursor.execute(sql, params)
            return cursor
        except Exception:
            cursor.close()
            raise

    @staticmethod
    def _timestamp(value: Any) -> str:
        if value is None:
            return ""
        return value.isoformat() if isinstance(value, datetime) else str(value)

    @staticmethod
    def _expected_decisions(register: DecisionRegister) -> tuple[tuple[Any, ...], ...]:
        return tuple(sorted(
            (
                item.decision_id,
                register.manifest_hash,
                item.kind,
                item.status,
                item.requires_human,
                item.automatic_action,
            )
            for item in register.pending
        ))

    def initialize(self, register: DecisionRegister) -> ReviewLedger:
        """Create the immutable batch/decision snapshot, or verify an existing one."""
        with PostgresUnitOfWork(self._connection_factory) as uow:
            connection = uow.connection
            cursor = self._run(
                connection,
                """
                INSERT INTO bravo_shadow.migration_review_batches
                    (batch_key, manifest_hash)
                VALUES (%s, %s)
                ON CONFLICT (batch_key) DO NOTHING
                """,
                (register.batch_id, register.manifest_hash),
            )
            cursor.close()

            cursor = self._run(
                connection,
                """
                SELECT manifest_hash
                FROM bravo_shadow.migration_review_batches
                WHERE batch_key = %s
                FOR UPDATE
                """,
                (register.batch_id,),
            )
            batch = cursor.fetchone()
            cursor.close()
            if batch is None or str(batch[0]).strip() != register.manifest_hash:
                raise ReviewValidationError("stored_batch_manifest_mismatch")

            for item in register.pending:
                cursor = self._run(
                    connection,
                    """
                    INSERT INTO bravo_shadow.migration_review_decisions
                        (decision_id, batch_key, manifest_hash, decision_kind,
                         decision_status, requires_human, automatic_action)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (decision_id) DO NOTHING
                    """,
                    (
                        item.decision_id,
                        register.batch_id,
                        register.manifest_hash,
                        item.kind,
                        item.status,
                        item.requires_human,
                        item.automatic_action,
                    ),
                )
                cursor.close()

            self._assert_decision_snapshot(connection, register)
            return self._load_from_connection(connection, register)

    def load(self, register: DecisionRegister) -> ReviewLedger:
        """Load an existing ledger; missing or drifted snapshots fail closed."""
        with PostgresUnitOfWork(self._connection_factory) as uow:
            return self._load_from_connection(uow.connection, register)

    def append(
        self,
        register: DecisionRegister,
        *,
        event_id: str,
        decision_id: str,
        expected_version: int,
        reviewer_id: str,
        choice: ReviewChoice,
        rationale: str,
        reviewed_at: str,
    ) -> ReviewLedger:
        """Append one review under a per-decision row lock and optimistic version."""
        with PostgresUnitOfWork(self._connection_factory) as uow:
            connection = uow.connection

            cursor = self._run(
                connection,
                """
                SELECT manifest_hash
                FROM bravo_shadow.migration_review_batches
                WHERE batch_key = %s
                """,
                (register.batch_id,),
            )
            batch = cursor.fetchone()
            cursor.close()
            if batch is None or str(batch[0]).strip() != register.manifest_hash:
                raise ReviewValidationError("stored_batch_manifest_mismatch")

            cursor = self._run(
                connection,
                """
                SELECT batch_key, manifest_hash
                FROM bravo_shadow.migration_review_decisions
                WHERE batch_key = %s AND decision_id = %s
                FOR UPDATE
                """,
                (register.batch_id, decision_id),
            )
            decision = cursor.fetchone()
            cursor.close()
            if decision is None:
                raise ReviewValidationError("unknown_or_uninitialized_decision")
            if decision[0] != register.batch_id or str(decision[1]).strip() != register.manifest_hash:
                raise ReviewValidationError("stored_decision_manifest_mismatch")

            self._assert_decision_snapshot(connection, register)
            current = self._load_from_connection(connection, register)

            cursor = self._run(
                connection,
                """
                SELECT COALESCE(MAX(version), 0)
                FROM bravo_shadow.migration_review_events
                WHERE batch_key = %s AND decision_id = %s
                """,
                (register.batch_id, decision_id),
            )
            row = cursor.fetchone()
            cursor.close()
            database_version = int(row[0]) if row else 0
            if database_version != expected_version:
                raise ReviewValidationError("stale_review_version")

            cursor = self._run(
                connection,
                """
                SELECT event_id
                FROM bravo_shadow.migration_review_events
                WHERE event_id = %s
                """,
                (event_id,),
            )
            duplicate_event = cursor.fetchone()
            cursor.close()
            if duplicate_event is not None:
                raise ReviewValidationError("duplicate_review_event_id")

            updated = append_review(
                current,
                register,
                event_id=event_id,
                decision_id=decision_id,
                expected_version=expected_version,
                reviewer_id=reviewer_id,
                choice=choice,
                rationale=rationale,
                reviewed_at=reviewed_at,
            )
            event = updated.events[-1]
            cursor = self._run(
                connection,
                """
                INSERT INTO bravo_shadow.migration_review_events
                    (event_id, batch_key, decision_id, manifest_hash, version,
                     reviewer_id, choice, rationale, reviewed_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    event.event_id,
                    register.batch_id,
                    event.decision_id,
                    register.manifest_hash,
                    event.version,
                    event.reviewer_id,
                    event.choice,
                    event.rationale,
                    event.reviewed_at,
                ),
            )
            cursor.close()
            return updated

    def _assert_decision_snapshot(self, connection: Any, register: DecisionRegister) -> None:
        cursor = self._run(
            connection,
            """
            SELECT decision_id, manifest_hash, decision_kind, decision_status,
                   requires_human, automatic_action
            FROM bravo_shadow.migration_review_decisions
            WHERE batch_key = %s
            ORDER BY decision_id
            """,
            (register.batch_id,),
        )
        rows = tuple(tuple(row) for row in cursor.fetchall())
        cursor.close()
        if rows != self._expected_decisions(register):
            raise ReviewValidationError("stored_decision_snapshot_mismatch")

    def _load_from_connection(self, connection: Any, register: DecisionRegister) -> ReviewLedger:
        cursor = self._run(
            connection,
            """
            SELECT manifest_hash
            FROM bravo_shadow.migration_review_batches
            WHERE batch_key = %s
            """,
            (register.batch_id,),
        )
        batch = cursor.fetchone()
        cursor.close()
        if batch is None:
            raise ReviewValidationError("review_batch_not_initialized")
        if str(batch[0]).strip() != register.manifest_hash:
            raise ReviewValidationError("stored_batch_manifest_mismatch")

        self._assert_decision_snapshot(connection, register)
        cursor = self._run(
            connection,
            """
            SELECT event_id, decision_id, manifest_hash, version, reviewer_id,
                   choice, rationale, reviewed_at
            FROM bravo_shadow.migration_review_events
            WHERE batch_key = %s
            ORDER BY decision_id, version
            """,
            (register.batch_id,),
        )
        rows = cursor.fetchall()
        cursor.close()

        if any(
            not isinstance(row, (tuple, list))
            or len(row) != 8
            or row[2] != register.manifest_hash
            for row in rows
        ):
            raise ReviewValidationError("stored_event_manifest_mismatch")

        ledger = ReviewLedger(
            batch_id=register.batch_id,
            manifest_hash=register.manifest_hash,
            events=tuple(
                ReviewEvent(
                    event_id=row[0],
                    decision_id=row[1],
                    version=row[3],
                    reviewer_id=row[4],
                    choice=row[5],
                    rationale=row[6],
                    reviewed_at=self._timestamp(row[7]),
                )
                for row in rows
            ),
        )
        if not verify_review_ledger(ledger, register):
            raise ReviewValidationError("stored_ledger_binding_or_integrity_error")
        return ledger
