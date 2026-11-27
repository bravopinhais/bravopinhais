"""Unified, read-only synthetic migration preflight assessment.

Combines structural inventory, target compatibility, specialized collection
contracts, per-record value checks, and confirmed exact-ID references. It never
builds import payloads, performs I/O, or returns source record values/IDs.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from app.core.migration_compatibility import CompatibilityReport, assess_source_compatibility
from app.core.migration_reference_reconciliation import (
    ReconciliationReport, reconcile_collection_references,
)
from app.core.migration_source_inventory import SourceInventory, inspect_source_collections
from app.core.migration_special_contracts import (
    SpecialContractReport, assess_special_contracts,
)
from app.core.migration_special_value_assessment import (
    RecordValueAssessment, assess_special_record_values,
)

@dataclass(frozen=True, slots=True)
class ValueAssessmentSummary:
    records_assessed: int
    records_with_issues: int
    issue_counts: tuple[tuple[str, int], ...]

@dataclass(frozen=True, slots=True)
class IntegratedMigrationPreflight:
    status: str
    source_inventory: SourceInventory
    compatibility: CompatibilityReport
    specialized_contracts: SpecialContractReport
    references: ReconciliationReport
    value_summary: ValueAssessmentSummary
    blocking_reasons: tuple[str, ...]

def _assess_values(collections: Mapping[str, Any]) -> ValueAssessmentSummary:
    supported = {"financeiro", "documentos", "estoque", "acertos_estoque"}
    counts: dict[str, int] = {}
    assessed = with_issues = 0
    for name in sorted(supported):
        records = collections.get(name)
        if not isinstance(records, (list, tuple)):
            continue
        for record in records:
            if not isinstance(record, Mapping):
                continue
            result: RecordValueAssessment = assess_special_record_values(name, record)
            assessed += 1
            if result.issues:
                with_issues += 1
            for issue in result.issues:
                counts[issue.code] = counts.get(issue.code, 0) + 1
    return ValueAssessmentSummary(
        records_assessed=assessed,
        records_with_issues=with_issues,
        issue_counts=tuple(sorted(counts.items())),
    )

def run_integrated_migration_preflight(
    collections: Any,
    *,
    compatibility_mapping: Mapping[str, str] | None = None,
    special_mapping: Mapping[str, str] | None = None,
) -> IntegratedMigrationPreflight:
    """Assess a supplied in-memory snapshot; caller must use synthetic data."""
    if not isinstance(collections, Mapping):
        empty = inspect_source_collections(collections)
        compatibility = assess_source_compatibility(empty, source_to_target=compatibility_mapping)
        special = assess_special_contracts(empty, source_to_target=special_mapping)
        references = reconcile_collection_references({})
        return IntegratedMigrationPreflight(
            "blocked", empty, compatibility, special, references,
            ValueAssessmentSummary(0, 0, ()),
            ("collections_not_object",),
        )

    inventory = inspect_source_collections(collections)
    compatibility = assess_source_compatibility(
        inventory, source_to_target=compatibility_mapping,
    )
    special = assess_special_contracts(inventory, source_to_target=special_mapping)
    references = reconcile_collection_references(collections)
    values = _assess_values(collections)

    reasons: list[str] = []
    if not inventory.valid_collection_container or inventory.issue_codes:
        reasons.append("source_inventory_has_structural_issues")
    if any(item.status not in {"compatible", "compatible_with_optional_gaps"}
           for item in compatibility.assessments):
        reasons.append("target_compatibility_requires_review")
    if compatibility.unmapped_source_collections or compatibility.unmapped_target_collections:
        reasons.append("collection_mapping_incomplete")
    if compatibility.mapping_conflicts:
        reasons.append("collection_mapping_conflict")
    if any(item.status != "references_resolved" for item in references.assessments):
        reasons.append("confirmed_references_require_review")
    if references.missing_collections or references.invalid_collection_containers:
        reasons.append("reference_collections_missing_or_invalid")
    if values.records_with_issues:
        reasons.append("record_value_contracts_have_issues")
    # Specialized contracts intentionally retain domain/business blockers
    # until field mappings, conversions and exception handling are approved.
    if special.assessments or special.unassessed_domains:
        reasons.append("specialized_domain_approval_pending")

    return IntegratedMigrationPreflight(
        status="review_required" if reasons else "assessment_clear_not_import_authorized",
        source_inventory=inventory,
        compatibility=compatibility,
        specialized_contracts=special,
        references=references,
        value_summary=values,
        blocking_reasons=tuple(sorted(set(reasons))),
    )
