"""Single privacy-safe, read-only migration readiness facade.

Combines structural integrity, detailed integrated assessment, batch preflight,
and export/reconciliation evidence. A clear assessment is never import approval.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Any

from app.core.migration_integrated_preflight import (
    IntegratedMigrationPreflight,
    run_integrated_migration_preflight,
)
from app.core.migration_pre_import_validation import (
    PreImportValidationReport,
)
from app.core.migration_readiness_report import (
    MigrationReadinessReport,
    build_migration_readiness_report,
)
from app.core.migration_report import PreflightReport
from app.core.migration_source_integrity import (
    SourceIntegrityReport,
    build_source_integrity_report,
)


@dataclass(frozen=True, slots=True)
class CompleteMigrationReadiness:
    status: str
    source_integrity: SourceIntegrityReport
    integrated_assessment: IntegratedMigrationPreflight
    batch_readiness: MigrationReadinessReport
    blocking_reasons: tuple[str, ...]


def build_complete_migration_readiness(
    collections: Any,
    *,
    preflight: PreflightReport,
    evidence: PreImportValidationReport,
    compatibility_mapping: Mapping[str, str] | None = None,
    special_mapping: Mapping[str, str] | None = None,
) -> CompleteMigrationReadiness:
    """Combine already-collected in-memory evidence; never performs I/O."""
    integrity = build_source_integrity_report(
        collections,
        compatibility_mapping=compatibility_mapping,
        special_mapping=special_mapping,
    ) if isinstance(collections, Mapping) else None
    integrated = run_integrated_migration_preflight(
        collections,
        compatibility_mapping=compatibility_mapping,
        special_mapping=special_mapping,
    )
    batch = build_migration_readiness_report(
        preflight=preflight,
        evidence=evidence,
    )

    blockers: set[str] = set(integrated.blocking_reasons)
    blockers.update(integrated.source_inventory.issue_codes)
    blockers.update(integrated.references.missing_collections)
    if integrity is None:
        blockers.add("collections_not_object")
    else:
        blockers.update(integrity.issue_codes)
    if not batch.ready:
        blockers.update(issue.code for issue in batch.issues)

    if not preflight.valid or not evidence.ready:
        status = "blocked"
    elif blockers:
        status = "review_required"
    else:
        status = "assessment_clear_not_import_authorized"

    return CompleteMigrationReadiness(
        status=status,
        source_integrity=integrity,
        integrated_assessment=integrated,
        batch_readiness=batch,
        blocking_reasons=tuple(sorted(blockers)),
    )
