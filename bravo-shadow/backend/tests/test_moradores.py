from fastapi.testclient import TestClient

from app.main import app, create_app

client = TestClient(app)


def setup_function() -> None:
    app.state.services.moradores._items.clear()


def test_resident_crud_and_filters():
    response = client.post("/api/v1/moradores", json={
        "bloco": "1", "apartamento": "101", "nome": "Ana Maria", "email": "ana@example.com",
        "telefone": "41999990000", "cpf": "123", "petNome": "Gato / Mimi", "vagaGaragem": "G12"
    })
    assert response.status_code == 201
    item = response.json()
    assert client.get("/api/v1/moradores?bloco=1&busca=ana").json()[0]["id"] == item["id"]
    assert client.put(f"/api/v1/moradores/{item['id']}", json={
        "bloco": "2", "apartamento": "202", "nome": "Ana Maria"
    }).status_code == 200
    assert client.delete(f"/api/v1/moradores/{item['id']}").status_code == 204


def test_resident_required_fields_and_import():
    assert client.post("/api/v1/moradores", json={"bloco": "1", "nome": "Ana"}).status_code == 422
    response = client.post("/api/v1/moradores/importar", json={"moradores": [
        {"bloco": "3", "apartamento": "301", "nome": "Carlos"},
        {"apartamento": "302", "nome": "Sem Nome"}
    ]})
    assert response.status_code == 200
    assert response.json()["importados"] == 2
    assert len(client.get("/api/v1/moradores").json()) == 2


def test_resident_not_found():
    assert client.delete("/api/v1/moradores/inexistente").status_code == 404


def test_residents_are_isolated_between_app_instances():
    first, second = TestClient(create_app()), TestClient(create_app())
    created = first.post("/api/v1/moradores", json={
        "bloco": "1", "apartamento": "101", "nome": "Morador Isolado"
    }).json()
    assert first.get("/api/v1/moradores").json()[0]["id"] == created["id"]
    assert second.get("/api/v1/moradores").json() == []
