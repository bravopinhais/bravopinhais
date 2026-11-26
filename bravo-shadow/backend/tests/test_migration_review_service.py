from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from app.core.authorization import AuthenticatedPrincipal
from app.core.migration_decisions import build_decision_register
from app.core.migration_review_service import MigrationReviewAccessDenied, MigrationReviewService
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


def test_batch_policy_denies_before_persistence(monkeypatch):
    import app.core.migration_review_service as service_module

    monkeypatch.setattr(service_module, "require_capability", lambda *_args: None)
    service, runtime, principal, register = setup_service()
    with pytest.raises(MigrationReviewAccessDenied, match="batch_access_not_approved"):
        service.append(
            principal,
            register,
            decision_id=register.pending[0].decision_id,
            expected_version=0,
            choice="keep_blocked",
            rationale="Aguardar conferência",
        )
    assert runtime.calls == []


def test_append_uses_google_subject_as_reviewer_not_client_input(monkeypatch):
    import app.core.migration_review_service as service_module

    monkeypatch.setattr(service_module, "require_capability", lambda *_args: None)
    service, runtime, principal, register = setup_service(
        can_access_batch=lambda actor, batch: actor.subject == principal.subject
        and batch == register.batch_id
    )
    service.append(
        principal,
        register,
        decision_id=register.pending[0].decision_id,
        expected_version=0,
        choice="keep_blocked",
        rationale="Aguardar conferência",
    )
    operation, payload = runtime.calls[0]
    assert operation == "append"
    assert payload["reviewer_id"] == "google-subject-123"
    assert payload["event_id"] == "event-fixed"
    assert payload["reviewed_at"] == "2026-11-26T00:00:00+00:00"


def test_empty_rationale_is_rejected_before_persistence(monkeypatch):
    import app.core.migration_review_service as service_module

    monkeypatch.setattr(service_module, "require_capability", lambda *_args: None)
    service, runtime, principal, register = setup_service(
        can_access_batch=lambda _principal, _batch: True
    )
    with pytest.raises(ValueError, match="rationale_required"):
        service.append(
            principal,
            register,
            decision_id=register.pending[0].decision_id,
            expected_version=0,
            choice="keep_blocked",
            rationale=" ",
        )
    assert runtime.calls == []
