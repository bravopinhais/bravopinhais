"""Append-only, versioned human review history for migration decisions.

The ledger is an in-memory value object. It records a human decision but never
changes a migration manifest, resolves a conflict, persists data, or executes
an import.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.core.migration_decisions import DecisionRegister


ReviewChoice = Literal[
    "approved_for_manual_resolution",
    "keep_blocked",
    "exclude_from_this_batch",
    "request_more_information",
]


@dataclass(frozen=True, slots=True)
class ReviewEvent:
    event_id: str
    decision_id: str
    version: int
    reviewer_id: str
    choice: ReviewChoice
    rationale: str
    reviewed_at: str


@dataclass(frozen=True, slots=True)
class ReviewLedger:
    batch_id: str
    manifest_hash: str
    events: tuple[ReviewEvent, ...]

    def version_for(self, decision_id: str) -> int:
        return sum(event.decision_id == decision_id for event in self.events)

    def history_for(self, decision_id: str) -> tuple[ReviewEvent, ...]:
        return tuple(event for event in self.events if event.decision_id == decision_id)


class ReviewValidationError(ValueError):
    """Raised when a review event is incomplete or stale."""


def create_review_ledger(register: DecisionRegister) -> ReviewLedger:
    """Start an empty append-only ledger bound to one batch and manifest."""
    return ReviewLedger(
        batch_id=register.batch_id,
        manifest_hash=register.manifest_hash,
        events=(),
    )


def append_review(
    ledger: ReviewLedger,
    register: DecisionRegister,
    *,
    event_id: str,
    decision_id: str,
    expected_version: int,
    reviewer_id: str,
    choice: ReviewChoice,
    rationale: str,
    reviewed_at: str,
) -> ReviewLedger:
    """Return a new ledger with one review event; the input remains unchanged.

    expected_version provides optimistic concurrency: the first review is
    version 1 and must expect version 0. Later reviews retain prior history.
    """
    if ledger.batch_id != register.batch_id or ledger.manifest_hash != register.manifest_hash:
        raise ReviewValidationError("ledger_batch_mismatch")
    if decision_id not in {item.decision_id for item in register.pending}:
        raise ReviewValidationError("unknown_decision")
    if not event_id.strip() or any(event.event_id == event_id for event in ledger.events):
        raise ReviewValidationError("duplicate_or_empty_event_id")
    if not reviewer_id.strip():
        raise ReviewValidationError("reviewer_required")
    if not rationale.strip():
        raise ReviewValidationError("rationale_required")
    if not reviewed_at.strip():
        raise ReviewValidationError("reviewed_at_required")
    if choice not in {
        "approved_for_manual_resolution",
        "keep_blocked",
        "exclude_from_this_batch",
        "request_more_information",
    }:
        raise ReviewValidationError("invalid_review_choice")

    current_version = ledger.version_for(decision_id)
    if expected_version != current_version:
        raise ReviewValidationError("stale_review_version")

    event = ReviewEvent(
        event_id=event_id,
        decision_id=decision_id,
        version=current_version + 1,
        reviewer_id=reviewer_id,
        choice=choice,
        rationale=rationale.strip(),
        reviewed_at=reviewed_at,
    )
    return ReviewLedger(
        batch_id=ledger.batch_id,
        manifest_hash=ledger.manifest_hash,
        events=ledger.events + (event,),
    )
