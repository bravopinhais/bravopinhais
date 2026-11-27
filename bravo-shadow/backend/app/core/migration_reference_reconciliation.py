"""Privacy-safe reconciliation of confirmed legacy collection references.

The reconciler is read-only and reports aggregate counts only. It never
returns source IDs, field values, or payload fragments and performs no I/O.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class ReferenceRule:
    key: str
    source_collection: str
    source_field: str
    target_collection: str
    target_field: str = "id"
    optional: bool = False


@dataclass(frozen=True, slots=True)
class ReferenceAssessment:
    key: str
    source_collection: str
    target_collection: str
    source_records: int
    target_records: int | None
    references_checked: int
    references_resolved: int
    orphan_references: int
    blank_optional_references: int
    invalid_reference_values: int
    source_records_missing_reference_field: int
    duplicate_target_ids: int
    target_records_missing_id: int
    status: str


@dataclass(frozen=True, slots=True)
class ReconciliationReport:
    assessments: tuple[ReferenceAssessment, ...]
    missing_collections: tuple[str, ...]
    invalid_collection_containers: tuple[str, ...]
    invalid_source_records: int


# Only relationships established by the audited legacy contract are listed.
# Additional relationships must be added after their source fields are proven.
CONFIRMED_REFERENCE_RULES: tuple[ReferenceRule, ...] = (
    ReferenceRule(
        key="financeiro_plano_contas",
        source_collection="financeiro",
        source_field="planoContaId",
        target_collection="plano_contas",
        optional=True,
    ),
    ReferenceRule(
        key="acertos_estoque_produtos",
        source_collection="acertos_estoque",
        source_field="produtoId",
        target_collection="estoque",
        optional=False,
    ),
)


def _valid_id(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def reconcile_collection_references(
    collections: Mapping[str, Any],
    *,
    rules: tuple[ReferenceRule, ...] = CONFIRMED_REFERENCE_RULES,
) -> ReconciliationReport:
    """Check exact-ID references and duplicate/missing target identities.

    A missing collection is distinct from an empty collection. Optional null
    or empty-string references are counted, not treated as resolved.
    """
    if not isinstance(collections, Mapping):
        raise TypeError("collections deve ser um objeto de coleções.")

    assessments: list[ReferenceAssessment] = []
    missing: set[str] = set()
    invalid_containers: set[str] = set()
    invalid_source_records = 0

    for rule in rules:
        source_raw = collections.get(rule.source_collection)
        target_raw = collections.get(rule.target_collection)
        source_present = rule.source_collection in collections
        target_present = rule.target_collection in collections

        if not source_present:
            missing.add(rule.source_collection)
        if not target_present:
            missing.add(rule.target_collection)

        source_valid = isinstance(source_raw, (list, tuple))
        target_valid = isinstance(target_raw, (list, tuple))
        if source_present and not source_valid:
            invalid_containers.add(rule.source_collection)
        if target_present and not target_valid:
            invalid_containers.add(rule.target_collection)

        source_records = source_raw if source_valid else ()
        target_records = target_raw if target_valid else ()
        invalid_source_records += sum(
            1 for record in source_records if not isinstance(record, Mapping)
        )

        target_ids: set[str] = set()
        duplicate_target_ids = 0
        target_missing_id = 0
        for record in target_records:
            if not isinstance(record, Mapping):
                continue
            target_id = record.get(rule.target_field)
            if not _valid_id(target_id):
                target_missing_id += 1
            elif target_id in target_ids:
                duplicate_target_ids += 1
            else:
                target_ids.add(target_id)

        checked = resolved = orphan = blank_optional = invalid_values = missing_field = 0
        for record in source_records:
            if not isinstance(record, Mapping):
                continue
            if rule.source_field not in record:
                missing_field += 1
                continue
            reference = record[rule.source_field]
            if reference is None or reference == "":
                if rule.optional:
                    blank_optional += 1
                else:
                    invalid_values += 1
                continue
            if not _valid_id(reference):
                invalid_values += 1
                continue
            checked += 1
            if not target_valid:
                continue
            if reference in target_ids:
                resolved += 1
            else:
                orphan += 1

        blockers = (
            not source_present or not target_present
            or not source_valid or not target_valid
            or not source_records or not target_records
            or orphan > 0 or invalid_values > 0 or missing_field > 0
            or duplicate_target_ids > 0 or target_missing_id > 0
            or any(not isinstance(item, Mapping) for item in source_records)
            or any(not isinstance(item, Mapping) for item in target_records)
        )
        if blockers:
            status = "review_required"
        else:
            status = "references_resolved"

        assessments.append(ReferenceAssessment(
            key=rule.key,
            source_collection=rule.source_collection,
            target_collection=rule.target_collection,
            source_records=len(source_records),
            target_records=len(target_records) if target_present and target_valid else None,
            references_checked=checked,
            references_resolved=resolved,
            orphan_references=orphan,
            blank_optional_references=blank_optional,
            invalid_reference_values=invalid_values,
            source_records_missing_reference_field=missing_field,
            duplicate_target_ids=duplicate_target_ids,
            target_records_missing_id=target_missing_id,
            status=status,
        ))

    return ReconciliationReport(
        assessments=tuple(assessments),
        missing_collections=tuple(sorted(missing)),
        invalid_collection_containers=tuple(sorted(invalid_containers)),
        invalid_source_records=invalid_source_records,
    )
