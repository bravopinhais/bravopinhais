"""PostgreSQL provenance adapter for immutable legacy-to-Shadow identity links.

This adapter never opens connections or writes business payloads. Callers pass
the connection already owned by the migration write unit of work.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class SourceRecordConflict(ValueError):
    """Raised when a source identity is already linked to different content/target."""


@dataclass(frozen=True, slots=True)
class SourceRecordLink:
    source_system: str
    source_collection: str
    legacy_id: str
    destination_collection: str
    destination_id: str
    source_record_hash: str
    batch_id: str


class PostgresSourceRecordStore:
    """Insert-or-verify source provenance; never silently retarget an identity."""

    @staticmethod
    def _run(connection: Any, sql: str, params: tuple[Any, ...]) -> Any:
        cursor = connection.cursor()
        try:
            cursor.execute(sql, params)
            return cursor
        except Exception:
            cursor.close()
            raise

    def record(self, connection: Any, link: SourceRecordLink) -> None:
        """Record provenance on the caller's transaction connection.

        Replaying the same source identity is idempotent only when the source
        hash and destination are unchanged. The original first_batch_id is
        preserved. A changed hash or destination requires human review.
        """
        values = (
            link.source_system,
            link.source_collection,
            link.legacy_id,
            link.destination_collection,
            link.destination_id,
            link.source_record_hash,
            link.batch_id,
        )
        if any(not isinstance(value, str) or not value.strip() for value in values):
            raise SourceRecordConflict("source_record_fields_required")
        if len(link.source_record_hash) != 64 or any(
            char not in "0123456789abcdef" for char in link.source_record_hash
        ):
            raise SourceRecordConflict("source_record_hash_invalid")

        cursor = self._run(
            connection,
            """
            INSERT INTO bravo_shadow.migration_source_records
                (source_system, source_collection, legacy_id,
                 destination_collection, destination_id, source_record_hash,
                 first_batch_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (source_system, source_collection, legacy_id) DO NOTHING
            RETURNING source_system
            """,
            values,
        )
        inserted = cursor.fetchone()
        cursor.close()
        if inserted is not None:
            return

        cursor = self._run(
            connection,
            """
            SELECT destination_collection, destination_id, source_record_hash
            FROM bravo_shadow.migration_source_records
            WHERE source_system = %s AND source_collection = %s AND legacy_id = %s
            FOR UPDATE
            """,
            values[:3],
        )
        existing = cursor.fetchone()
        cursor.close()
        if existing is None:
            raise SourceRecordConflict("source_record_conflict_unresolved")
        if tuple(existing) != (
            link.destination_collection,
            link.destination_id,
            link.source_record_hash,
        ):
            raise SourceRecordConflict("source_record_identity_or_content_conflict")

    def mark_verified(
        self,
        connection: Any,
        *,
        source_system: str,
        source_collection: str,
        legacy_id: str,
        destination_collection: str,
        destination_id: str,
        source_record_hash: str,
        batch_id: str,
    ) -> None:
        """Advance verification provenance only for an already verified batch.

        The caller must invoke this after the complete batch verification has
        succeeded, using the same transaction connection. The guarded UPDATE
        rejects missing/changed provenance and batches that are not in the
        verified state; the composite FK also enforces the source system.
        """
        values = (
            source_system,
            source_collection,
            legacy_id,
            destination_collection,
            destination_id,
            source_record_hash,
            batch_id,
            source_system,
        )
        if any(not isinstance(value, str) or not value.strip() for value in values):
            raise SourceRecordConflict("source_record_verification_fields_required")
        if len(source_record_hash) != 64 or any(
            char not in "0123456789abcdef" for char in source_record_hash
        ):
            raise SourceRecordConflict("source_record_hash_invalid")

        cursor = self._run(
            connection,
            """
            UPDATE bravo_shadow.migration_source_records AS source
            SET last_verified_batch_id = %s,
                updated_at = now()
            WHERE source.source_system = %s
              AND source.source_collection = %s
              AND source.legacy_id = %s
              AND source.destination_collection = %s
              AND source.destination_id = %s
              AND source.source_record_hash = %s
              AND EXISTS (
                  SELECT 1
                  FROM bravo_shadow.migration_batches AS batch
                  WHERE batch.batch_id = %s
                    AND batch.source_system = %s
                    AND batch.status = 'verified'
              )
            RETURNING source.source_system
            """,
            (
                batch_id,
                source_system,
                source_collection,
                legacy_id,
                destination_collection,
                destination_id,
                source_record_hash,
                batch_id,
                source_system,
            ),
        )
        updated = cursor.fetchone()
        cursor.close()
        if updated is None:
            raise SourceRecordConflict("source_record_verification_not_eligible")
