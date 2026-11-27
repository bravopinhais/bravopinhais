"""Consolidated, privacy-safe source integrity assessment for migration.

This is a read-only assessment facade. It does not transform records, build
payloads, access files, connect to a database, or persist reports.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from app.core.migration_compatibility import (
    CompatibilityReport,
    assess_source_compatibility,
)
from app.core.migration_reference_reconciliation import (
    ReconciliationReport,
    reconcile_collection_references,
)
from app.core.migration_source_inventory import (
    SourceInventory,
    inspect_source_collections,
)
from app.core.migration_special_contracts import (
    SpecialContractReport,
    assess_special_contracts,
)


@dataclass(frozen=True, slots=True)
class IntegritySummary:
    collection_count: int
    record_count: int
    invalid_records: int
    records_missing_id: int
    duplicate_ids: int
    collections_with_issues: int
    compatibility_review_collections: int
    special_contracts_requiring_review: int
    orphan_references: int
    unresolved_reference_rules: int
    missing_collections: int
    invalid_collection_containers: int
    unassessed_special_domains: int
    status: str


@dataclass(frozen=True, slots=True)
class SourceIntegrityReport:
    summary: IntegritySummary
    inventory: SourceInventory
    compatibility: CompatibilityReport
    special_contracts: SpecialContractReport
    references: ReconciliationReport
    issue_codes: tuple[str, ...]


def build_source_integrity_report(
    collections: Mapping[str, Any],
    *,
    compatibility_mapping: Mapping[str, str] | None = None,
    special_mapping: Mapping[str, str] | None = None,
) -> SourceIntegrityReport:
    """Build one aggregate report from an already-decoded collections object.

    Collection mappings are explicit and independent for the standard and
    special contracts. The caller remains responsible for proving aliases.
    """
    inventory = inspect_source_collections(collections)
    compatibility = assess_source_compatibility(
        inventory, source_to_target=compatibility_mapping
    )
    special = assess_special_contracts(
        inventory, source_to_target=special_mapping
    )
    references = reconcile_collection_references(collections)

    record_count = sum(item.records_total for item in inventory.collections)
    invalid_records = sum(item.invalid_records for item in inventory.collections)
    missing_ids = sum(item.records_missing_id for item in inventory.collections)
    duplicate_ids = sum(item.duplicate_ids for item in inventory.collections)
    collections_with_issues = sum(
        1 for item in inventory.collections
        if item.invalid_records or item.records_missing_id or item.duplicate_ids
    )
    compatibility_reviews = sum(
        1 for item in compatibility.assessments
        if item.status not in {"compatible", "compatible_with_optional_gaps"}
    )
    special_reviews = sum(
        1 for item in special.assessments
        if item.status != "shape_matches_review_required"
    )
    orphan_references = sum(
        item.orphan_references for item in references.assessments
    )
    unresolved_rules = sum(
        1 for item in references.assessments
        if item.status != "references_resolved"
    )

    issues = set(inventory.issue_codes)
    if invalid_records:
        issues.add("invalid_records_present")
    if missing_ids:
        issues.add("records_missing_id")
    if duplicate_ids:
        issues.add("duplicate_ids_present")
    if compatibility_reviews:
        issues.add("compatibility_review_required")
    if compatibility.unmapped_source_collections:
        issues.add("unmapped_source_collections")
    if compatibility.unmapped_target_collections:
        issues.add("unmapped_target_collections")
    if compatibility.mapping_conflicts:
        issues.add("compatibility_mapping_conflicts")
    if special_reviews:
        issues.add("special_contract_review_required")
    if special.unassessed_domains:
        issues.add("special_domains_unassessed")
    if orphan_references:
        issues.add("orphan_references_present")
    if unresolved_rules:
        issues.add("reference_rules_unresolved")
    if references.missing_collections:
        issues.add("reference_collections_missing")
    if references.invalid_collection_containers:
        issues.add("invalid_reference_collection_containers")

    status = "review_required" if issues else "structurally_clear"
    summary = IntegritySummary(
        collection_count=len(inventory.collections),
        record_count=record_count,
        invalid_records=invalid_records,
        records_missing_id=missing_ids,
        duplicate_ids=duplicate_ids,
        collections_with_issues=collections_with_issues,
        compatibility_review_collections=compatibility_reviews,
        special_contracts_requiring_review=special_reviews,
        orphan_references=orphan_references,
        unresolved_reference_rules=unresolved_rules,
        missing_collections=len(references.missing_collections),
        invalid_collection_containers=len(references.invalid_collection_containers),
        unassessed_special_domains=len(special.unassessed_domains),
        status=status,
    )
    return SourceIntegrityReport(
        summary=summary,
        inventory=inventory,
        compatibility=compatibility,
        special_contracts=special,
        references=references,
        issue_codes=tuple(sorted(issues)),
    )
