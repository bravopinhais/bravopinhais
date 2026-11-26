"""Read-only PostgreSQL snapshot reader for Shadow migration provenance.

The caller owns the connection and transaction. The first statement marks the
transaction READ ONLY; this adapter never commits, rolls back, or opens a
connection. It reads provenance metadata only, never business payloads.
"""
from __future__ import annotations

from typing import Any

from app.core.migration_identity import SourceIdentity
from app.core.migration_reconciliation import DestinationProvenance


class ProvenanceSnapshotReadError(RuntimeError):
    """Raised when a consistent read-only provenance snapshot cannot be built."""


class PostgresProvenanceSnapshotReader:
    """Read the provenance inventory inside a caller-owned read-only transaction."""

    def read(self, connection: Any) -> tuple[DestinationProvenance, ...]:
        cursor = connection.cursor()
        try:
            # Must be the first command in the transaction. PostgreSQL rejects
            # this if the caller already performed a write in the transaction.
            cursor.execute("SET TRANSACTION READ ONLY")
            cursor.execute(
                """
                SELECT source_system, source_collection, legacy_id,
                       source_record_hash, destination_collection, destination_id
                FROM bravo_shadow.migration_source_records
                ORDER BY source_system, source_collection, legacy_id
                """
            )
            rows = cursor.fetchall()
        except Exception as exc:
            raise ProvenanceSnapshotReadError(
                "provenance_snapshot_read_failed"
            ) from exc
        finally:
            cursor.close()

        try:
            snapshot = tuple(
                DestinationProvenance(
                    identity=SourceIdentity(
                        source_system=row[0],
                        source_collection=row[1],
                        legacy_id=row[2],
                    ),
                    source_record_hash=row[3],
                    destination_collection=row[4],
                    destination_id=row[5],
                )
                for row in rows
            )
        except (IndexError, TypeError, ValueError) as exc:
            raise ProvenanceSnapshotReadError(
                "provenance_snapshot_invalid_row"
            ) from exc
        return snapshot
