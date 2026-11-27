from fastapi.testclient import TestClient

from app.main import app

import pytest
from types import MappingProxyType

from app.core.authentication import get_current_principal
from app.core.authorization import AuthenticatedPrincipal, CAPABILITIES
from app.core import authorization

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
    service.create(FinanceiroInput(**payload(planoContaId="pc_linked")))
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
    with pytest.raises(Exception):
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
