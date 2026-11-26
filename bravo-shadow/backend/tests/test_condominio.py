from fastapi.testclient import TestClient
from app.main import app
from app.modules.condominio.service import condominio_service

client = TestClient(app)

def setup_function() -> None:
    condominio_service._data.clear()

def test_condominium_patch_preserves_unedited_fields():
    client.put("/api/v1/condominio", json={"razaoSocial":"Condomínio Exemplo","cidade":"Curitiba"})
    response = client.put("/api/v1/condominio", json={"nome":"Residencial Exemplo","telefone":"4133330000"})
    assert response.status_code == 200
    data = response.json()
    assert data["razaoSocial"] == "Condomínio Exemplo"
    assert data["cidade"] == "Curitiba"
    assert data["nome"] == "Residencial Exemplo"
    assert data["telefone"] == "4133330000"

def test_condominium_rejects_unknown_fields():
    assert client.put("/api/v1/condominio", json={"campoInventado":"x"}).status_code == 422
