"""Fail-closed application service for human migration review.

Not mounted on an API route. Capabilities and batch-access policy must be
formally approved before any caller can use this service.
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from uuid import uuid4

from app.core.authorization import AuthenticatedPrincipal, require_capability
from app.core.migration_decisions import DecisionRegister
from app.core.migration_review import ReviewChoice, ReviewLedger, ReviewValidationError


READ_CAPABILITY = "migration_review:read"
APPEND_CAPABILITY = "migration_review:append"


class MigrationReviewAccessDenied(PermissionError):
    """Raised when the principal is not authorized for the requested batch."""


class MigrationReviewService:
    """Authorize a person and a batch before touching the persistence adapter.

    The batch policy defaults to deny. This is intentional: there is currently
    no approved per-batch ACL. The service never trusts a reviewer ID from a
    request; it derives the persisted actor from principal.subject.
    """

    def __init__(
        self,
        runtime_store: object,
        *,
        can_access_batch: Callable[[AuthenticatedPrincipal, str], bool] | None = None,
        event_id_factory: Callable[[], str] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._runtime_store = runtime_store
        self._can_access_batch = can_access_batch or (lambda _principal, _batch: False)
        self._event_id_factory = event_id_factory or (lambda: str(uuid4()))
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def _authorize_batch(self, principal: AuthenticatedPrincipal, register: DecisionRegister) -> None:
        if not self._can_access_batch(principal, register.batch_id):
            raise MigrationReviewAccessDenied("batch_access_not_approved")

    def load(
        self, principal: AuthenticatedPrincipal, register: DecisionRegister
    ) -> ReviewLedger:
        require_capability(principal, READ_CAPABILITY)
        self._authorize_batch(principal, register)
        return self._runtime_store.load(register)

    def append(
        self,
        principal: AuthenticatedPrincipal,
        register: DecisionRegister,
        *,
        decision_id: str,
        expected_version: int,
        choice: ReviewChoice,
        rationale: str,
    ) -> ReviewLedger:
        require_capability(principal, APPEND_CAPABILITY)
        self._authorize_batch(principal, register)
        if not isinstance(rationale, str) or not rationale.strip():
            raise ReviewValidationError("rationale_required")
        reviewed_at = self._clock().astimezone(timezone.utc).isoformat()
        return self._runtime_store.append(
            register,
            event_id=self._event_id_factory(),
            decision_id=decision_id,
            expected_version=expected_version,
            reviewer_id=principal.subject,
            choice=choice,
            rationale=rationale,
            reviewed_at=reviewed_at,
        )
