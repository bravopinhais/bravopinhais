from fastapi.testclient import TestClient

from app.main import app
from app.modules.contas_bancarias.service import contas_bancarias_service

client = TestClient(app)


def setup_function() -> None:
    contas_bancarias_service._items.clear()


def test_create_list_update_delete_bank_account():
    created = client.post(
        "/api/v1/contas-bancarias",
        json={"banco": "Banco do Brasil", "saldo": 1250.5},
    )
    assert created.status_code == 201
    item = created.json()
    assert item["saldo"] == 1250.5
    updated = client.put(
        f"/api/v1/contas-bancarias/{item['id']}",
        json={"banco": "Caixa", "saldo": 800},
    )
    assert updated.status_code == 200
    assert updated.json()["banco"] == "Caixa"
    assert client.delete(f"/api/v1/contas-bancarias/{item['id']}").status_code == 204
    assert client.get("/api/v1/contas-bancarias").json() == []


def test_default_balance_and_missing_delete():
    created = client.post("/api/v1/contas-bancarias", json={"banco": "Cooperativa"})
    assert created.status_code == 201
    assert created.json()["saldo"] == 0.0
    assert client.delete("/api/v1/contas-bancarias/missing").status_code == 404


def test_bank_name_is_required():
    assert client.post("/api/v1/contas-bancarias", json={"banco": ""}).status_code == 422
