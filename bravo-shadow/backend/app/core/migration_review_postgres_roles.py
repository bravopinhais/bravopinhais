"""Role-separated facades for the PostgreSQL migration review ledger.

The database grants remain the actual security boundary. These facades prevent
normal application wiring from accidentally exposing snapshot initialization
through the runtime service interface.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.core.migration_decisions import DecisionRegister
from app.core.migration_review import ReviewChoice, ReviewLedger
from app.core.migration_review_postgres import PostgresReviewLedgerStore


class PostgresReviewSnapshotInitializer:
    """Preparation-only facade; wire only to a controlled migration credential."""

    __slots__ = ("__store",)

    def __init__(self, connection_factory: Callable[[], Any]) -> None:
        self.__store = PostgresReviewLedgerStore(connection_factory)

    def initialize(self, register: DecisionRegister) -> ReviewLedger:
        return self.__store.initialize(register)


class PostgresReviewRuntimeStore:
    """Runtime facade exposing read and append only, never snapshot creation."""

    __slots__ = ("__store",)

    def __init__(self, connection_factory: Callable[[], Any]) -> None:
        self.__store = PostgresReviewLedgerStore(connection_factory)

    def load(self, register: DecisionRegister) -> ReviewLedger:
        return self.__store.load(register)

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
        return self.__store.append(
            register,
            event_id=event_id,
            decision_id=decision_id,
            expected_version=expected_version,
            reviewer_id=reviewer_id,
            choice=choice,
            rationale=rationale,
            reviewed_at=reviewed_at,
        )
