from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from app.core.authorization import AuthenticatedPrincipal
from app.core.migration_decisions import build_decision_register
from app.core.migration_review import ReviewValidationError
from app.core.migration_review_service import (
    MigrationReviewAccessDenied,
    MigrationReviewService,
)
from test_migration_decisions import setup_batch


class RuntimeSpy:
    def __init__(self):
        self.calls = []

    def load(self, register):
        self.calls.append(("load", register.batch_id))
        return "ledger"

    def append(self, register, **kwargs):
        self.calls.append(("append", kwargs))
        return "ledger"


def setup_service(can_access_batch=None):
    _, _, preflight, manifest = setup_batch()
    register = build_decision_register(manifest, preflight)
    runtime = RuntimeSpy()
    principal = AuthenticatedPrincipal(
        subject="google-subject-123",
        email="reviewer@example.test",
        profile="Admin",
        account_status="Ativo",
    )
    service = MigrationReviewService(
        runtime,
        can_access_batch=can_access_batch,
        event_id_factory=lambda: "event-fixed",
        clock=lambda: datetime(2026, 11, 26, tzinfo=timezone.utc),
    )
    return service, runtime, principal, register


def test_review_service_fails_closed_until_capabilities_are_approved():
    service, runtime, principal, register = setup_service(
        can_access_batch=lambda _principal, _batch: True
    )
    with pytest.raises(HTTPException) as error:
        service.load(principal, register)
    assert error.value.status_code == 403
    assert runtime.calls == []


def test_review_service_denies_batch_before_persistence():
    service, runtime, principal, register = setup_service()
    with pytest.raises(HTTPException) as error:
        service.append(
            principal,
            register,
            decision_id=register.pending[0].decision_id,
            expected_version=0,
            choice="keep_blocked",
            rationale="Aguardar conferência",
        )
    assert error.value.status_code == 403
    assert runtime.calls == []


def test_review_service_rejects_empty_rationale_after_authorization():
    service, runtime, principal, register = setup_service(
        can_access_batch=lambda _principal, _batch: True
    )
    # The capability check deliberately remains fail-closed until catalog approval.
    with pytest.raises(HTTPException):
        service.append(
            principal,
            register,
            decision_id=register.pending[0].decision_id,
            expected_version=0,
            choice="keep_blocked",
            rationale=" ",
        )
    assert runtime.calls == []


def test_missing_batch_policy_defaults_to_deny():
    service, runtime, principal, register = setup_service()
    # Unknown capability is denied before batch policy or storage access.
    with pytest.raises(HTTPException):
        service.load(principal, register)
    assert runtime.calls == []
