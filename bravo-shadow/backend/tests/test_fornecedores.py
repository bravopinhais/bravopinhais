from fastapi.testclient import TestClient

from app.main import app, create_app

client = TestClient(app)


def setup_function() -> None:
    app.state.services.fornecedores._items.clear()


def test_supplier_crud():
    response = client.post("/api/v1/fornecedores", json={"cnpj": "12.345.678/0001-90", "razaoSocial": "Fornecedor Exemplo"})
    assert response.status_code == 201
    item = response.json()
    assert item["cnpj"] == "12.345.678/0001-90"
    updated = client.put(f"/api/v1/fornecedores/{item['id']}", json={"cnpj": "123", "razaoSocial": "Nome Atualizado"})
    assert updated.status_code == 200
    assert updated.json()["razaoSocial"] == "Nome Atualizado"
    assert client.delete(f"/api/v1/fornecedores/{item['id']}").status_code == 204
    assert client.get("/api/v1/fornecedores").json() == []


def test_supplier_required_fields_and_not_found():
    assert client.post("/api/v1/fornecedores", json={"cnpj": "123"}).status_code == 422
    assert client.put("/api/v1/fornecedores/nao-existe", json={"cnpj": "123", "razaoSocial": "Teste"}).status_code == 404


def test_suppliers_are_isolated_between_app_instances():
    first, second = TestClient(create_app()), TestClient(create_app())
    created = first.post("/api/v1/fornecedores", json={"cnpj": "123", "razaoSocial": "Fornecedor Isolado"}).json()
    assert first.get("/api/v1/fornecedores").json()[0]["id"] == created["id"]
    assert second.get("/api/v1/fornecedores").json() == []


def test_supplier_fields_are_trimmed_and_cnpj_format_is_preserved():
    response = client.post("/api/v1/fornecedores", json={
        "cnpj": " 12.345.678/0001-90 ",
        "razaoSocial": "  Empresa Exemplo Ltda  "
    })
    assert response.status_code == 201
    assert response.json()["cnpj"] == "12.345.678/0001-90"
    assert response.json()["razaoSocial"] == "Empresa Exemplo Ltda"


def test_supplier_required_fields_reject_whitespace_only_values():
    response = client.post("/api/v1/fornecedores", json={
        "cnpj": "   ", "razaoSocial": " Empresa Exemplo "
    })
    assert response.status_code == 422


def test_supplier_update_trims_fields():
    created = client.post("/api/v1/fornecedores", json={
        "cnpj": "123", "razaoSocial": "Empresa"
    }).json()
    response = client.put(f"/api/v1/fornecedores/{created['id']}", json={
        "cnpj": "  123  ", "razaoSocial": "  Nome Atualizado  "
    })
    assert response.status_code == 200
    assert response.json()["cnpj"] == "123"
    assert response.json()["razaoSocial"] == "Nome Atualizado"
