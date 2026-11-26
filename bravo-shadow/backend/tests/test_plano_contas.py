from fastapi.testclient import TestClient

from app.main import app
from app.modules.plano_contas.service import plano_contas_service

client = TestClient(app)


def setup_function() -> None:
    plano_contas_service._items.clear()


def payload(**overrides):
    data = {"codigo": "1.1", "nome": "Taxa Ordinária", "tipo": "Receita"}
    data.update(overrides)
    return data


def test_create_and_list_account():
    created = client.post("/api/v1/plano-contas", json=payload())
    assert created.status_code == 201
    assert created.json()["codigo"] == "1.1"
    assert len(client.get("/api/v1/plano-contas").json()) == 1


def test_reject_duplicate_code_case_insensitive():
    assert client.post("/api/v1/plano-contas", json=payload()).status_code == 201
    duplicate = client.post("/api/v1/plano-contas", json=payload(codigo="1.1"))
    assert duplicate.status_code == 409


def test_update_account():
    created = client.post("/api/v1/plano-contas", json=payload()).json()
    updated = client.put(
        f"/api/v1/plano-contas/{created['id']}",
        json=payload(nome="Taxa atualizada", tipo="Despesa"),
    )
    assert updated.status_code == 200
    assert updated.json()["nome"] == "Taxa atualizada"
    assert updated.json()["tipo"] == "Despesa"


def test_delete_account():
    created = client.post("/api/v1/plano-contas", json=payload()).json()
    deleted = client.delete(f"/api/v1/plano-contas/{created['id']}")
    assert deleted.status_code == 204
    assert client.get("/api/v1/plano-contas").json() == []


def test_invalid_type_is_rejected():
    response = client.post("/api/v1/plano-contas", json=payload(tipo="Transferência"))
    assert response.status_code == 422
