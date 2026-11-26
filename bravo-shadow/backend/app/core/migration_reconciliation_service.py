"""Read-only orchestration for source inventory vs PostgreSQL Shadow provenance.

The source inventory is supplied by the caller as an immutable tuple. This
service never connects to the legacy system, opens/closes a connection,
commits/rolls back, writes records, or authorizes an import.
"""
from __future__ import annotations

from app.core.migration_provenance_snapshot_postgres import (
    PostgresProvenanceSnapshotReader,
)
from app.core.migration_reconciliation import (
    ReconciliationReport,
    SourceSnapshotRecord,
    reconcile_source_and_shadow,
)


def reconcile_postgres_provenance(
    *,
    connection: object,
    source_records: tuple[SourceSnapshotRecord, ...],
    reader: PostgresProvenanceSnapshotReader | None = None,
) -> ReconciliationReport:
    """Compare caller-provided source inventory with read-only Shadow metadata.

    The caller must provide a connection with a fresh transaction: the reader
    issues SET TRANSACTION READ ONLY as its first SQL statement. Transaction
    lifecycle remains entirely caller-owned.
    """
    if not isinstance(source_records, tuple):
        raise TypeError("source_records deve ser uma tupla imutável.")
    if any(not isinstance(item, SourceSnapshotRecord) for item in source_records):
        raise TypeError("source_records contém item de tipo inválido.")

    snapshot_reader = reader or PostgresProvenanceSnapshotReader()
    provenance_records = snapshot_reader.read(connection)
    return reconcile_source_and_shadow(source_records, provenance_records)
