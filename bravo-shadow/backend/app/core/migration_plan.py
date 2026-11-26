"""Read-only dry-run planning for synthetic Bravo migration batches.

The planner consumes an already parsed batch plus snapshots supplied by the
caller. It performs no I/O and never writes to a destination database.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Literal

from app.core.migration_identity import (
    ExistingSourceMapping,
    SourceIdentity,
    classify_source_identity,
)

PlanStatus = Literal[
    "ready",
    "already_applied",
    "conflict_changed_source",
    "destination_id_collision",
    "mapping_inconsistent",
    "blocked_duplicate_source",
    "blocked_unresolved_reference",
]


@dataclass(frozen=True, slots=True)
class DryRunCandidate:
    identity: SourceIdentity
    source_record_hash: str
    destination_id_exists: bool = False
    existing_mapping: ExistingSourceMapping | None = None
    references: tuple[SourceIdentity, ...] = ()


@dataclass(frozen=True, slots=True)
class DryRunRecord:
    identity: SourceIdentity
    status: PlanStatus
    base_classification: str
    unresolved_references: tuple[SourceIdentity, ...]
    may_insert: bool


@dataclass(frozen=True, slots=True)
class DryRunSummary:
    total: int
    ready: int
    already_applied: int
    blocked: int
    conflicts: int


@dataclass(frozen=True, slots=True)
class DryRunPlan:
    records: tuple[DryRunRecord, ...]
    summary: DryRunSummary


def build_dry_run_plan(
    candidates: tuple[DryRunCandidate, ...],
    *,
    already_known_sources: frozenset[SourceIdentity] = frozenset(),
) -> DryRunPlan:
    """Build a deterministic, in-memory plan without performing writes.

    References resolve only against identities present in this batch or
    explicitly supplied as already known by the caller. No fuzzy matching or
    destination-ID guessing is performed.
    """
    identity_counts = Counter(candidate.identity for candidate in candidates)
    batch_identities = frozenset(identity_counts)
    available_sources = batch_identities | already_known_sources

    planned: list[DryRunRecord] = []
    for candidate in candidates:
        decision = classify_source_identity(
            incoming_hash=candidate.source_record_hash,
            existing_mapping=candidate.existing_mapping,
            destination_id_exists=candidate.destination_id_exists,
        )
        unresolved = tuple(
            reference
            for reference in candidate.references
            if reference not in available_sources
        )

        if identity_counts[candidate.identity] > 1:
            status: PlanStatus = "blocked_duplicate_source"
            may_insert = False
        elif decision.classification != "ready":
            status = decision.classification
            may_insert = False
        elif unresolved:
            status = "blocked_unresolved_reference"
            may_insert = False
        else:
            status = "ready"
            may_insert = True

        planned.append(
            DryRunRecord(
                identity=candidate.identity,
                status=status,
                base_classification=decision.classification,
                unresolved_references=unresolved,
                may_insert=may_insert,
            )
        )

    records = tuple(planned)
    summary = DryRunSummary(
        total=len(records),
        ready=sum(record.status == "ready" for record in records),
        already_applied=sum(record.status == "already_applied" for record in records),
        blocked=sum(
            record.status in ("blocked_duplicate_source", "blocked_unresolved_reference")
            for record in records
        ),
        conflicts=sum(
            record.status in (
                "conflict_changed_source",
                "destination_id_collision",
                "mapping_inconsistent",
            )
            for record in records
        ),
    )
    return DryRunPlan(records=records, summary=summary)
