"""Pure, deterministic reconciliation between a source snapshot and Shadow provenance.

This module is intentionally in-memory and read-only. It performs no I/O,
database access, persistence, repair, or migration authorization.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass

from app.core.migration_identity import SourceIdentity


@dataclass(frozen=True, slots=True)
class SourceSnapshotRecord:
    identity: SourceIdentity
    source_record_hash: str

    def __post_init__(self) -> None:
        _validate_hash(self.source_record_hash)


@dataclass(frozen=True, slots=True)
class DestinationProvenance:
    identity: SourceIdentity
    source_record_hash: str
    destination_collection: str
    destination_id: str

    def __post_init__(self) -> None:
        _validate_hash(self.source_record_hash)
        for field_name in ("destination_collection", "destination_id"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} deve ser texto não vazio.")


@dataclass(frozen=True, slots=True)
class ReconciliationReport:
    valid: bool
    matched: int
    missing_mapping: int
    changed_source_hash: int
    orphaned_mapping: int
    duplicate_source_mapping: int
    duplicate_destination: int
    issues: tuple[str, ...]


def _validate_hash(value: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise ValueError("source_record_hash deve ser SHA-256 hexadecimal minúsculo.")


def reconcile_source_and_shadow(
    source_records: tuple[SourceSnapshotRecord, ...],
    provenance_records: tuple[DestinationProvenance, ...],
) -> ReconciliationReport:
    """Compare source inventory with Shadow provenance without changing either."""
    sources_by_id: dict[SourceIdentity, list[SourceSnapshotRecord]] = defaultdict(list)
    mappings_by_id: dict[SourceIdentity, list[DestinationProvenance]] = defaultdict(list)
    destinations: Counter[tuple[str, str]] = Counter()

    for record in source_records:
        sources_by_id[record.identity].append(record)
    for record in provenance_records:
        mappings_by_id[record.identity].append(record)
        destinations[(record.destination_collection, record.destination_id)] += 1

    duplicate_source_count = sum(
        len(records) for records in sources_by_id.values() if len(records) > 1
    ) + sum(len(records) for records in mappings_by_id.values() if len(records) > 1)
    duplicate_destination_count = sum(
        1 for count in destinations.values() if count > 1
    )

    matched = 0
    missing_mapping = 0
    changed_hash = 0
    orphaned_mapping = 0
    issue_codes: set[str] = set()

    all_identities = set(sources_by_id) | set(mappings_by_id)
    for identity in sorted(
        all_identities,
        key=lambda item: (item.source_system, item.source_collection, item.legacy_id),
    ):
        source_rows = sources_by_id.get(identity, [])
        mapping_rows = mappings_by_id.get(identity, [])

        if not source_rows:
            orphaned_mapping += len(mapping_rows)
            issue_codes.add("orphaned_mapping")
            continue
        if not mapping_rows:
            missing_mapping += 1
            issue_codes.add("missing_mapping")
            continue
        if len(source_rows) != 1 or len(mapping_rows) != 1:
            issue_codes.add("duplicate_source_mapping")
            continue
        if source_rows[0].source_record_hash != mapping_rows[0].source_record_hash:
            changed_hash += 1
            issue_codes.add("changed_source_hash")
            continue
        matched += 1

    if duplicate_source_count:
        issue_codes.add("duplicate_source_mapping")
    if duplicate_destination_count:
        issue_codes.add("duplicate_destination")

    ordered_issues = tuple(sorted(issue_codes))
    valid = not ordered_issues
    return ReconciliationReport(
        valid=valid,
        matched=matched,
        missing_mapping=missing_mapping,
        changed_source_hash=changed_hash,
        orphaned_mapping=orphaned_mapping,
        duplicate_source_mapping=duplicate_source_count,
        duplicate_destination=duplicate_destination_count,
        issues=ordered_issues,
    )
