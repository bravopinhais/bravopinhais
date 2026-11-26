"""Thread-safe in-memory persistence port for migration review history.

This adapter is a Shadow-only prototype. It stores immutable review ledgers in
process memory; it is not durable across restarts and is not a PostgreSQL
implementation. All writes remain append-only and use optimistic versions.
"""
from __future__ import annotations

from threading import RLock
from typing import Protocol

from app.core.migration_decisions import DecisionRegister
from app.core.migration_review import (
    ReviewChoice,
    ReviewLedger,
    ReviewValidationError,
    append_review,
    create_review_ledger,
    verify_review_ledger,
)


class ReviewLedgerStore(Protocol):
    """Storage contract for a ledger bound to one batch and manifest."""

    def load(self, register: DecisionRegister) -> ReviewLedger: ...

    def append(
        self,
        register: DecisionRegister,
        *,
        event_id: str,
        decision_id: str,
        expected_version: int,
        reviewer_id: str,
        choice: ReviewChoice,
        rationale: str,
        reviewed_at: str,
    ) -> ReviewLedger: ...


class InMemoryReviewLedgerStore:
    """Atomic, append-only in-memory adapter for review events.

    The lock covers version check and append, so concurrent requests using the
    same expected version cannot both succeed. A batch key cannot be rebound
    to a different manifest hash.
    """

    def __init__(self) -> None:
        self._lock = RLock()
        self._ledgers: dict[str, ReviewLedger] = {}

    def load(self, register: DecisionRegister) -> ReviewLedger:
        with self._lock:
            ledger = self._ledgers.get(register.batch_id)
            if ledger is None:
                ledger = create_review_ledger(register)
                self._ledgers[register.batch_id] = ledger
            if not verify_review_ledger(ledger, register):
                raise ReviewValidationError("stored_ledger_binding_or_integrity_error")
            return ledger

    def append(
        self,
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
        with self._lock:
            current = self.load(register)
            updated = append_review(
                current,
                register,
                event_id=event_id,
                decision_id=decision_id,
                expected_version=expected_version,
                reviewer_id=reviewer_id,
                choice=choice,
                rationale=rationale,
                reviewed_at=reviewed_at,
            )
            self._ledgers[register.batch_id] = updated
            return updated

