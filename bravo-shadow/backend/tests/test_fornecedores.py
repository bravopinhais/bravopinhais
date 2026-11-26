from fastapi.testclient import TestClient
from app.main import app
from app.modules.fornecedores.service import fornecedores_service

client = TestClient(app)

def setup_function() -> None:
    fornecedores_service._items.clear()

def test_supplier_crud():
    response = client.post("/api/v1/fornecedores", json={"cnpj":"12.345.678/0001-90","razaoSocial":"Fornecedor Exemplo"})
    assert response.status_code == 201
    item = response.json()
    assert item["cnpj"] == "12.345.678/0001-90"
    updated = client.put(f"/api/v1/fornecedores/{item['id']}", json={"cnpj":"123","razaoSocial":"Nome Atualizado"})
    assert updated.status_code == 200
    assert updated.json()["razaoSocial"] == "Nome Atualizado"
    assert client.delete(f"/api/v1/fornecedores/{item['id']}").status_code == 204
    assert client.get("/api/v1/fornecedores").json() == []

def test_supplier_required_fields_and_not_found():
    assert client.post("/api/v1/fornecedores", json={"cnpj":"123"}).status_code == 422
    assert client.put("/api/v1/fornecedores/nao-existe", json={"cnpj":"123","razaoSocial":"Teste"}).status_code == 404
