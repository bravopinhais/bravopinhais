from fastapi.testclient import TestClient

from app.main import app
from app.modules.financeiro.schemas import FinanceiroInput
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
    financeiro_service.create(FinanceiroInput(**payload(planoContaId="pc_linked")))
    assert financeiro_service.has_plan_account_reference("pc_linked") is True
    assert financeiro_service.has_plan_account_reference("pc_unused") is False


def test_reject_invalid_title_type():
    response = client.post("/api/v1/financeiro", json=payload(tipo="Transferência"))
    assert response.status_code == 422


def test_reject_amount_with_more_than_two_decimal_places():
    response = client.post("/api/v1/financeiro", json=payload(valor=10.123))
    assert response.status_code == 422


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
