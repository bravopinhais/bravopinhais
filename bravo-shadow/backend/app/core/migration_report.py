"""Human-readable, read-only report for Bravo migration preflight results."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Mapping

from app.core.migration_plan import DryRunCandidate
from app.core.migration_preflight import PreflightResult


@dataclass(frozen=True, slots=True)
class CollectionReport:
    collection: str
    envelope_records: int
    candidates: int
    ready: int
    already_applied: int
    blocked: int
    conflicts: int
    not_planned: int


@dataclass(frozen=True, slots=True)
class PreflightReport:
    valid: bool
    collections: tuple[CollectionReport, ...]
    total_envelope_records: int
    total_candidates: int
    ready: int
    already_applied: int
    blocked: int
    conflicts: int
    not_planned: int
    issue_count: int
    issue_codes: tuple[str, ...]


def build_preflight_report(
    envelope: Any,
    candidates: tuple[DryRunCandidate, ...],
    result: PreflightResult,
) -> PreflightReport:
    """Summarize a preflight without changing or reclassifying its decisions."""
    collection_names: set[str] = set()
    envelope_counts: Counter[str] = Counter()

    if isinstance(envelope, Mapping):
        raw_collections = envelope.get("collections")
        if isinstance(raw_collections, Mapping):
            for name, records in raw_collections.items():
                if isinstance(name, str):
                    collection_names.add(name)
                    if isinstance(records, list):
                        envelope_counts[name] = len(records)

    candidate_counts = Counter(candidate.identity.source_collection for candidate in candidates)
    collection_names.update(candidate_counts.keys())

    planned_statuses: dict[str, Counter[str]] = {
        name: Counter() for name in collection_names
    }
    if result.plan is not None:
        # The planner preserves input order, so each result maps to its candidate.
        for candidate, record in zip(candidates, result.plan.records):
            planned_statuses.setdefault(candidate.identity.source_collection, Counter())[
                record.status
            ] += 1

    rows: list[CollectionReport] = []
    for name in sorted(collection_names):
        statuses = planned_statuses.get(name, Counter())
        ready = statuses["ready"]
        applied = statuses["already_applied"]
        blocked = statuses["blocked_duplicate_source"] + statuses[
            "blocked_unresolved_reference"
        ]
        conflicts = (
            statuses["conflict_changed_source"]
            + statuses["destination_id_collision"]
            + statuses["mapping_inconsistent"]
        )
        planned = ready + applied + blocked + conflicts
        rows.append(
            CollectionReport(
                collection=name,
                envelope_records=envelope_counts[name],
                candidates=candidate_counts[name],
                ready=ready,
                already_applied=applied,
                blocked=blocked,
                conflicts=conflicts,
                not_planned=max(candidate_counts[name] - planned, 0)
                + max(envelope_counts[name] - candidate_counts[name], 0),
            )
        )

    totals = {
        field: sum(getattr(row, field) for row in rows)
        for field in (
            "ready",
            "already_applied",
            "blocked",
            "conflicts",
            "not_planned",
        )
    }
    issue_codes = tuple(issue.code for issue in result.issues)

    return PreflightReport(
        valid=result.valid,
        collections=tuple(rows),
        total_envelope_records=sum(envelope_counts.values()),
        total_candidates=len(candidates),
        ready=totals["ready"],
        already_applied=totals["already_applied"],
        blocked=totals["blocked"],
        conflicts=totals["conflicts"],
        not_planned=totals["not_planned"],
        issue_count=len(result.issues),
        issue_codes=issue_codes,
    )
