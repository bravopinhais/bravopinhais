from fastapi.testclient import TestClient

from app.main import create_app


def test_condominium_patch_preserves_unedited_fields():
    client = TestClient(create_app())
    client.put("/api/v1/condominio", json={"razaoSocial": "Condomínio Exemplo", "cidade": "Curitiba"})
    response = client.put("/api/v1/condominio", json={"nome": "Residencial Exemplo", "telefone": "4133330000"})
    assert response.status_code == 200
    data = response.json()
    assert data["razaoSocial"] == "Condomínio Exemplo"
    assert data["cidade"] == "Curitiba"
    assert data["nome"] == "Residencial Exemplo"
    assert data["telefone"] == "4133330000"


def test_condominium_rejects_unknown_fields():
    client = TestClient(create_app())
    assert client.put("/api/v1/condominio", json={"campoInventado": "x"}).status_code == 422


def test_condominium_is_isolated_between_app_instances():
    first, second = TestClient(create_app()), TestClient(create_app())
    first.put("/api/v1/condominio", json={"nome": "Condomínio A"})
    assert first.get("/api/v1/condominio").json()["nome"] == "Condomínio A"
    assert second.get("/api/v1/condominio").json()["nome"] is None
