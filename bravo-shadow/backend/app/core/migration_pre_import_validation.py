"""Pure pre-import gate combining snapshot, export chain and reconciliation.

This module is read-only: it accepts already collected, immutable evidence and
never reads a source, opens a database connection, writes data, or authorizes
an import by itself.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.core.migration_export_chain import verify_export_chain
from app.core.migration_export_manifest import ExportManifest, verify_export_manifest
from app.core.migration_reconciliation import ReconciliationReport
from app.core.migration_source_snapshot import SourceSnapshot, calculate_snapshot_hash


@dataclass(frozen=True, slots=True)
class PreImportValidationReport:
    ready: bool
    source_system: str
    export_id: str
    snapshot_records: int
    reconciliation_matched: int
    blockers: tuple[str, ...]


def validate_pre_import_evidence(
    *,
    snapshot: SourceSnapshot,
    manifest: ExportManifest,
    export_chain: tuple[ExportManifest, ...],
    reconciliation: ReconciliationReport,
    expected_previous_manifest_hash: str | None = None,
) -> PreImportValidationReport:
    """Evaluate evidence consistency; readiness is not permission to import."""
    if not isinstance(snapshot, SourceSnapshot):
        raise TypeError("snapshot deve ser SourceSnapshot.")
    if not isinstance(manifest, ExportManifest):
        raise TypeError("manifest deve ser ExportManifest.")
    if not isinstance(reconciliation, ReconciliationReport):
        raise TypeError("reconciliation deve ser ReconciliationReport.")
    if not isinstance(export_chain, tuple):
        raise TypeError("export_chain deve ser uma tupla imutável.")

    blockers: list[str] = []
    try:
        snapshot_hash = calculate_snapshot_hash(snapshot.source_system, snapshot.records)
        if snapshot_hash != snapshot.snapshot_hash:
            blockers.append("snapshot_hash_invalid")
    except (TypeError, ValueError, AttributeError):
        blockers.append("snapshot_invalid")

    if not verify_export_manifest(manifest):
        blockers.append("manifest_hash_invalid")
    if manifest.source_system != snapshot.source_system:
        blockers.append("source_system_mismatch")
    if manifest.source_baseline != snapshot.source_baseline:
        blockers.append("source_baseline_mismatch")
    if manifest.snapshot_hash != snapshot.snapshot_hash:
        blockers.append("snapshot_hash_mismatch")
    if manifest.record_count != len(snapshot.records):
        blockers.append("record_count_mismatch")
    if manifest.exported_at != snapshot.exported_at:
        blockers.append("export_timestamp_mismatch")

    chain_report = verify_export_chain(
        export_chain,
        expected_previous_manifest_hash=expected_previous_manifest_hash,
    )
    if not chain_report.valid:
        blockers.extend(f"export_chain:{issue}" for issue in chain_report.issues)
    if not export_chain:
        blockers.append("export_chain_empty")
    elif export_chain[-1].manifest_hash != manifest.manifest_hash:
        blockers.append("manifest_not_chain_tip")

    if not reconciliation.valid:
        blockers.extend(f"reconciliation:{issue}" for issue in reconciliation.issues)

    ordered_blockers = tuple(dict.fromkeys(blockers))
    return PreImportValidationReport(
        ready=not ordered_blockers,
        source_system=snapshot.source_system,
        export_id=manifest.export_id,
        snapshot_records=len(snapshot.records),
        reconciliation_matched=reconciliation.matched,
        blockers=ordered_blockers,
    )
