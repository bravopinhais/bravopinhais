from fastapi.testclient import TestClient

from app.main import app
from pydantic import ValidationError

import pytest
from types import MappingProxyType

from app.core.authentication import get_current_principal
from app.core.authorization import AuthenticatedPrincipal, CAPABILITIES
from app.core import authorization
from app.core.repositories import InMemoryCollectionRepository


class _TestAuditSink:
    """Auditoria efêmera de teste; não representa persistência PostgreSQL."""

    def __init__(self):
        self.events = []

    def append_in_transaction(self, connection, event):
        self.events.append(event)


class _AuditedMemoryFinanceiroRepository(InMemoryCollectionRepository):
    """Fake transacional para exercitar rotas autenticadas sem DB real."""

    def add_audited(self, item, event, audit_sink):
        with self._lock:
            if item.id in self._items:
                raise AssertionError("ID duplicado no fake de teste.")
            self._items[item.id] = item
            try:
                audit_sink.append_in_transaction(None, event)
            except BaseException:
                self._items.pop(item.id, None)
                raise

    def replace_if_version_audited(self, item, expected_version, event, audit_sink):
        with self._lock:
            current = self._items.get(item.id)
            if current is None:
                return self._missing()
            if current.version != expected_version:
                return self._conflict()
            updated = item.model_copy(update={"version": expected_version + 1})
            self._items[item.id] = updated
            try:
                audit_sink.append_in_transaction(None, event)
            except BaseException:
                self._items[item.id] = current
                raise
            return expected_version + 1

    def delete_audited(self, item_id, event, audit_sink):
        with self._lock:
            current = self._items.pop(item_id, None)
            if current is None:
                from fastapi import HTTPException
                raise HTTPException(status_code=404, detail="Título não encontrado.")
            try:
                audit_sink.append_in_transaction(None, event)
            except BaseException:
                self._items[item_id] = current
                raise

    @staticmethod
    def _missing():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Título não encontrado.")

    @staticmethod
    def _conflict():
        from fastapi import HTTPException
        raise HTTPException(status_code=409, detail="O título foi alterado por outra operação.")


def configure_test_auth(application):
    async def authenticated_admin():
        return AuthenticatedPrincipal(
            subject="google-test-subject",
            email="teste@example.com",
            profile="Admin",
            account_status="Ativo",
        )
    application.dependency_overrides[get_current_principal] = authenticated_admin


@pytest.fixture(autouse=True)
def allow_test_admin(monkeypatch):
    monkeypatch.setattr(
        authorization,
        "ROLE_CAPABILITIES",
        MappingProxyType({"Admin": CAPABILITIES, "Operador": frozenset()}),
    )
    configure_test_auth(app)
    service = app.state.services.financeiro
    repository = _AuditedMemoryFinanceiroRepository()
    sink = _TestAuditSink()
    service.repository = repository
    service._items = repository._items
    service.audit_sink = sink
    yield
    app.dependency_overrides.clear()


from app.modules.financeiro.schemas import FinanceiroInput

client = TestClient(app)


def setup_function() -> None:
    app.state.services.financeiro._items.clear()


def payload(**overrides):
    data = {
        "tipo": "Receber",
        "planoContaId": "",
        "historico": "Taxa condominial",
        "valor": 350.75,
    }
    data.update(overrides)
    return data


def test_create_and_list_financial_title():
    response = client.post("/api/v1/financeiro", json=payload())
    assert response.status_code == 201
    body = response.json()
    assert body["tipo"] == "Receber"
    assert body["planoContaId"] == ""
    assert body["valor"] == 350.75
    assert len(client.get("/api/v1/financeiro").json()) == 1


def test_create_payable_title_with_plan_account():
    response = client.post(
        "/api/v1/financeiro",
        json=payload(tipo="Pagar", planoContaId="pc_test"),
    )
    assert response.status_code == 201
    assert response.json()["planoContaId"] == "pc_test"


def test_update_replaces_title_fields():
    created = client.post("/api/v1/financeiro", json=payload()).json()
    updated = client.put(
        f"/api/v1/financeiro/{created['id']}",
        json=payload(tipo="Pagar", historico="Conta de água", valor=120),
        headers={"If-Match": f'"{created["version"]}"'},
    )
    assert updated.status_code == 200
    assert updated.json()["tipo"] == "Pagar"
    assert updated.json()["historico"] == "Conta de água"
    assert updated.json()["valor"] == 120


def test_update_missing_title_returns_404():
    response = client.put("/api/v1/financeiro/inexistente", json=payload(), headers={"If-Match": '"1"'})
    assert response.status_code == 404


def test_delete_title():
    created = client.post("/api/v1/financeiro", json=payload()).json()
    response = client.delete(f"/api/v1/financeiro/{created['id']}")
    assert response.status_code == 204
    assert client.get("/api/v1/financeiro").json() == []


def test_plan_account_reference_checker():
    service = app.state.services.financeiro
    service.create(
        FinanceiroInput(**payload(planoContaId="pc_linked")),
        actor=AuthenticatedPrincipal(
            subject="google-test-subject",
            email="teste@example.com",
            profile="Admin",
            account_status="Ativo",
        ),
    )
    assert service.has_plan_account_reference("pc_linked") is True
    assert service.has_plan_account_reference("pc_unused") is False


def test_reject_invalid_title_type():
    response = client.post("/api/v1/financeiro", json=payload(tipo="Transferência"))
    assert response.status_code == 422


def test_reject_amount_with_more_than_two_decimal_places():
    response = client.post("/api/v1/financeiro", json=payload(valor=10.123))
    assert response.status_code == 422


@pytest.mark.parametrize("valor", ["NaN", "Infinity", "-Infinity"])
def test_reject_non_finite_financial_amounts(valor):
    with pytest.raises(ValidationError):
        FinanceiroInput(**payload(valor=valor))


def test_reject_amount_exceeding_numeric_precision():
    response = client.post("/api/v1/financeiro", json=payload(valor=1000000000000.00))
    assert response.status_code == 422


def test_update_requires_if_match_header():
    created = client.post("/api/v1/financeiro", json=payload()).json()
    response = client.put(f"/api/v1/financeiro/{created['id']}", json=payload(valor=99))
    assert response.status_code == 428


def test_update_rejects_stale_if_match_version():
    created = client.post("/api/v1/financeiro", json=payload()).json()
    first = client.put(
        f"/api/v1/financeiro/{created['id']}",
        json=payload(valor=99),
        headers={"If-Match": '"1"'},
    )
    assert first.status_code == 200
    assert first.json()["version"] == 2
    stale = client.put(
        f"/api/v1/financeiro/{created['id']}",
        json=payload(valor=88),
        headers={"If-Match": '"1"'},
    )
    assert stale.status_code == 409
    assert client.get("/api/v1/financeiro").json()[0]["valor"] == 99


def test_create_returns_etag_header():
    response = client.post("/api/v1/financeiro", json=payload())
    assert response.status_code == 201
    assert response.headers["etag"] == '"1"'


def test_update_rejects_unquoted_if_match():
    created = client.post("/api/v1/financeiro", json=payload()).json()
    response = client.put(
        f"/api/v1/financeiro/{created['id']}",
        json=payload(),
        headers={"If-Match": "1"},
    )
    assert response.status_code == 400


def test_financial_history_is_trimmed():
    response = client.post(
        "/api/v1/financeiro",
        json=payload(historico="  Taxa de manutenção  "),
    )
    assert response.status_code == 201
    assert response.json()["historico"] == "Taxa de manutenção"


def test_financial_history_cannot_be_only_whitespace():
    response = client.post(
        "/api/v1/financeiro",
        json=payload(historico="   "),
    )
    assert response.status_code == 422


def test_plan_account_reference_is_trimmed():
    response = client.post(
        "/api/v1/financeiro",
        json=payload(planoContaId="  pc_test  "),
    )
    assert response.status_code == 201
    assert response.json()["planoContaId"] == "pc_test"


def test_plan_account_reference_uses_repository_optimized_checker():
    service = app.state.services.financeiro
    calls = []

    def optimized_checker(account_id):
        calls.append(account_id)
        return account_id == "pc_fast"

    service.repository.has_plan_account_reference = optimized_checker
    assert service.has_plan_account_reference("pc_fast") is True
    assert service.has_plan_account_reference("pc_other") is False
    assert calls == ["pc_fast", "pc_other"]
    del service.repository.has_plan_account_reference
