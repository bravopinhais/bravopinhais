"""Pure, read-only reconciliation between source inventory and Shadow provenance."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Literal

from app.core.migration_identity import SourceIdentity

ReconciliationStatus = Literal[
    "matched",
    "missing_mapping",
    "changed_source_hash",
    "duplicate_source_mapping",
    "duplicate_destination",
    "orphaned_mapping",
]


@dataclass(frozen=True, slots=True)
class SourceSnapshotRecord:
    identity: SourceIdentity
    source_record_hash: str


@dataclass(frozen=True, slots=True)
class DestinationProvenance:
    identity: SourceIdentity
    source_record_hash: str
    destination_collection: str
    destination_id: str


@dataclass(frozen=True, slots=True)
class ReconciliationIssue:
    status: ReconciliationStatus
    identity: SourceIdentity
    detail: str


@dataclass(frozen=True, slots=True)
class ReconciliationReport:
    valid: bool
    source_records: int
    provenance_records: int
    matched: int
    missing_mapping: int
    changed_source_hash: int
    duplicate_source_mapping: int
    duplicate_destination: int
    orphaned_mapping: int
    issues: tuple[ReconciliationIssue, ...]


def reconcile_source_and_shadow(
    source_records: tuple[SourceSnapshotRecord, ...],
    provenance_records: tuple[DestinationProvenance, ...],
) -> ReconciliationReport:
    """Compare two supplied snapshots without querying or mutating persistence.

    Duplicate source identities, reused destination identities, hash drift,
    missing links and links absent from the source inventory are reported.
    No issue is auto-corrected and a report with any issue is invalid.
    """
    issues: list[ReconciliationIssue] = []
    source_counts = Counter(item.identity for item in source_records)
    provenance_counts = Counter(item.identity for item in provenance_records)
    destination_counts = Counter(
        (item.destination_collection, item.destination_id)
        for item in provenance_records
    )

    source_by_identity: dict[SourceIdentity, SourceSnapshotRecord] = {}
    provenance_by_identity: dict[SourceIdentity, DestinationProvenance] = {}
    for item in source_records:
        source_by_identity.setdefault(item.identity, item)
    for item in provenance_records:
        provenance_by_identity.setdefault(item.identity, item)

    for identity, count in sorted(
        source_counts.items(),
        key=lambda pair: (pair[0].source_system, pair[0].source_collection, pair[0].legacy_id),
    ):
        if count > 1:
            issues.append(ReconciliationIssue(
                "duplicate_source_mapping", identity,
                f"Identidade aparece {count} vezes no inventário de origem.",
            ))

    for identity, count in sorted(
        provenance_counts.items(),
        key=lambda pair: (pair[0].source_system, pair[0].source_collection, pair[0].legacy_id),
    ):
        if count > 1:
            issues.append(ReconciliationIssue(
                "duplicate_source_mapping", identity,
                f"Identidade possui {count} vínculos de proveniência.",
            ))

    for destination, count in sorted(destination_counts.items()):
        if count > 1:
            identity = next(
                item.identity for item in provenance_records
                if (item.destination_collection, item.destination_id) == destination
            )
            issues.append(ReconciliationIssue(
                "duplicate_destination", identity,
                f"Destino {destination[0]}/{destination[1]} está associado a múltiplas origens.",
            ))

    for identity, source in source_by_identity.items():
        mapped = provenance_by_identity.get(identity)
        if mapped is None:
            issues.append(ReconciliationIssue(
                "missing_mapping", identity, "Registro de origem sem vínculo no Shadow.",
            ))
        elif mapped.source_record_hash != source.source_record_hash:
            issues.append(ReconciliationIssue(
                "changed_source_hash", identity,
                "Hash da origem difere do hash registrado na proveniência.",
            ))

    for identity in provenance_by_identity.keys() - source_by_identity.keys():
        issues.append(ReconciliationIssue(
            "orphaned_mapping", identity,
            "Vínculo de proveniência não existe no inventário de origem informado.",
        ))

    counts = Counter(issue.status for issue in issues)
    matched = sum(
        1 for identity, source in source_by_identity.items()
        if identity in provenance_by_identity
        and provenance_by_identity[identity].source_record_hash == source.source_record_hash
        and source_counts[identity] == 1
        and provenance_counts[identity] == 1
        and destination_counts[(
            provenance_by_identity[identity].destination_collection,
            provenance_by_identity[identity].destination_id,
        )] == 1
    )
    return ReconciliationReport(
        valid=not issues,
        source_records=len(source_records),
        provenance_records=len(provenance_records),
        matched=matched,
        missing_mapping=counts["missing_mapping"],
        changed_source_hash=counts["changed_source_hash"],
        duplicate_source_mapping=counts["duplicate_source_mapping"],
        duplicate_destination=counts["duplicate_destination"],
        orphaned_mapping=counts["orphaned_mapping"],
        issues=tuple(issues),
    )
