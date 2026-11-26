from fastapi.testclient import TestClient

from app.main import app
from app.modules.financeiro.service import financeiro_service

client = TestClient(app)


def setup_function() -> None:
    financeiro_service._items.clear()


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
    )
    assert updated.status_code == 200
    assert updated.json()["tipo"] == "Pagar"
    assert updated.json()["historico"] == "Conta de água"
    assert updated.json()["valor"] == 120


def test_update_missing_title_returns_404():
    response = client.put("/api/v1/financeiro/inexistente", json=payload())
    assert response.status_code == 404


def test_delete_title():
    created = client.post("/api/v1/financeiro", json=payload()).json()
    response = client.delete(f"/api/v1/financeiro/{created['id']}")
    assert response.status_code == 204
    assert client.get("/api/v1/financeiro").json() == []


def test_plan_account_reference_checker():
    financeiro_service.create(payload(planoContaId="pc_linked"))
    assert financeiro_service.has_plan_account_reference("pc_linked") is True
    assert financeiro_service.has_plan_account_reference("pc_unused") is False


def test_reject_invalid_title_type():
    response = client.post("/api/v1/financeiro", json=payload(tipo="Transferência"))
    assert response.status_code == 422
