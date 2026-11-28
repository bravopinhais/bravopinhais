from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.core.authorization import AuthenticatedPrincipal
from app.modules.configuracoes.service import ConfiguracoesService, MODULES


class FakeSettingsRepository:
    def __init__(self):
        self.states = {}
        self.events = []

    def list_states(self):
        return dict(self.states)

    def set_state_audited(self, key, enabled, *, event, audit_sink):
        self.states[key] = enabled
        audit_sink.append_in_transaction(None, event)
        self.events.append(event)

    def set_states_audited(self, changes, *, events, audit_sink):
        for (key, enabled), event in zip(changes.items(), events, strict=True):
            self.states[key] = enabled
            audit_sink.append_in_transaction(None, event)
            self.events.append(event)


class FakeAuditSink:
    def __init__(self):
        self.events = []

    def append_in_transaction(self, connection, event):
        self.events.append(event)


def admin():
    return AuthenticatedPrincipal(
        subject="google-subject-admin",
        email="admin@example.test",
        profile="Admin",
        account_status="Ativo",
    )


def operator():
    return AuthenticatedPrincipal(
        subject="google-subject-operator",
        email="operator@example.test",
        profile="Operador",
        account_status="Ativo",
    )


def service():
    repository = FakeSettingsRepository()
    audit = FakeAuditSink()
    return ConfiguracoesService(repository, audit), repository, audit


def test_module_catalog_defaults_to_active_and_matches_legacy_navigation():
    configured, _, _ = service()
    modules = configured.list_modules()

    assert len(modules) == 17
    assert {item.chave for item in modules} == {item[0] for item in MODULES}
    assert all(item.ativo for item in modules)


def test_admin_can_change_module_and_change_is_audited():
    configured, repository, audit = service()

    result = configured.set_module(
        "estoque", False, actor=admin(), request_id="req-test"
    )

    assert result.chave == "estoque"
    assert result.ativo is False
    assert repository.states["estoque"] is False
    assert len(audit.events) == 1
    assert audit.events[0].action == "configuracoes:alterar_modulo"
    assert audit.events[0].entity_id == "estoque"


def test_operator_cannot_change_module_state():
    configured, repository, audit = service()

    with pytest.raises(HTTPException) as error:
        configured.set_module("estoque", False, actor=operator())

    assert error.value.status_code == 403
    assert repository.states == {}
    assert audit.events == []


def test_configurations_module_cannot_be_disabled():
    configured, repository, audit = service()

    with pytest.raises(HTTPException) as error:
        configured.set_module("configuracoes", False, actor=admin())

    assert error.value.status_code == 409
    assert repository.states == {}
    assert audit.events == []


def test_bulk_deactivation_keeps_configurations_enabled_and_audits_each_module():
    configured, repository, audit = service()

    modules = configured.apply_bulk("desativar_operacionais", actor=admin())

    assert len(modules) == 17
    assert repository.states["configuracoes"] is True
    assert len(repository.states) == 17
    assert len(audit.events) == 17
    assert repository.states["configuracoes"] is True
    assert all(not value for key, value in repository.states.items() if key != "configuracoes")


def test_unknown_module_is_rejected_without_mutation():
    configured, repository, audit = service()

    with pytest.raises(HTTPException) as error:
        configured.set_module("unknown", True, actor=admin())

    assert error.value.status_code == 404
    assert repository.states == {}
    assert audit.events == []
