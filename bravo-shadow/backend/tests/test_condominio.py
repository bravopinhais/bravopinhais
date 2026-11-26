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



def test_condominium_patch_trims_values_and_preserves_omitted_fields():
    client = TestClient(create_app())
    client.put("/api/v1/condominio", json={"nome": "  Residencial Exemplo  ", "cidade": " Curitiba "})
    response = client.put("/api/v1/condominio", json={"telefone": "  (41) 3333-0000  ", "email": "  contato@example.com "})
    assert response.status_code == 200
    data = response.json()
    assert data["nome"] == "Residencial Exemplo"
    assert data["cidade"] == "Curitiba"
    assert data["telefone"] == "(41) 3333-0000"
    assert data["email"] == "contato@example.com"


def test_condominium_patch_accepts_empty_optional_values():
    client = TestClient(create_app())
    response = client.put("/api/v1/condominio", json={"telefone": "   ", "email": "  "})
    assert response.status_code == 200
    assert response.json()["telefone"] == ""
    assert response.json()["email"] == ""
