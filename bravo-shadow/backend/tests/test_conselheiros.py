from fastapi.testclient import TestClient

from app.main import create_app


def test_council_crud_and_optional_fields():
    client = TestClient(create_app())
    response = client.post("/api/v1/conselheiros", json={"nome": "Pessoa Exemplo", "cargo": "Síndico"})
    assert response.status_code == 201
    item = response.json()
    assert item["BlocoAp"] == ""
    assert item["telefone"] == ""
    updated = client.put(f"/api/v1/conselheiros/{item['id']}", json={
        "nome": "Pessoa Exemplo", "cargo": "Conselheiro", "BlocoAp": "Bloco 2 / 301", "telefone": "41999990000"
    })
    assert updated.status_code == 200
    assert client.delete(f"/api/v1/conselheiros/{item['id']}").status_code == 204


def test_council_required_fields_and_not_found():
    client = TestClient(create_app())
    assert client.post("/api/v1/conselheiros", json={"nome": "Pessoa"}).status_code == 422
    assert client.put("/api/v1/conselheiros/inexistente", json={"nome": "Pessoa", "cargo": "Síndico"}).status_code == 404


def test_council_members_are_isolated_between_app_instances():
    first, second = TestClient(create_app()), TestClient(create_app())
    first.post("/api/v1/conselheiros", json={"nome": "Pessoa", "cargo": "Síndico"})
    assert len(first.get("/api/v1/conselheiros").json()) == 1
    assert second.get("/api/v1/conselheiros").json() == []



def test_council_member_fields_are_trimmed_and_phone_format_preserved():
    client = TestClient(create_app())
    response = client.post("/api/v1/conselheiros", json={
        "nome": "  Pessoa Exemplo ", "cargo": " Síndico ",
        "BlocoAp": " Bloco 2 / 301 ", "telefone": " (41) 99999-0000 "
    })
    assert response.status_code == 201
    item = response.json()
    assert item["nome"] == "Pessoa Exemplo"
    assert item["cargo"] == "Síndico"
    assert item["BlocoAp"] == "Bloco 2 / 301"
    assert item["telefone"] == "(41) 99999-0000"


def test_council_required_fields_reject_whitespace_only_values():
    client = TestClient(create_app())
    response = client.post("/api/v1/conselheiros", json={"nome": " Pessoa ", "cargo": "   "})
    assert response.status_code == 422


def test_council_update_trims_optional_values():
    client = TestClient(create_app())
    created = client.post("/api/v1/conselheiros", json={"nome": "Pessoa", "cargo": "Síndico"}).json()
    response = client.put(f"/api/v1/conselheiros/{created['id']}", json={
        "nome": " Pessoa Atualizada ", "cargo": " Conselheiro ", "BlocoAp": "  ", "telefone": "  "
    })
    assert response.status_code == 200
    assert response.json()["nome"] == "Pessoa Atualizada"
    assert response.json()["BlocoAp"] == ""
    assert response.json()["telefone"] == ""
