from fastapi.testclient import TestClient

from app.main import app, create_app

client = TestClient(app)


def setup_function() -> None:
    app.state.services.empregados._items.clear()


def test_employee_crud_and_optional_fields():
    response = client.post("/api/v1/empregados", json={"nome": "Maria Exemplo", "cargo": "Zeladora"})
    assert response.status_code == 201
    item = response.json()
    assert item["empresa"] == ""
    assert item["contatoEmergenciaTel"] == ""
    updated = client.put(f"/api/v1/empregados/{item['id']}", json={
        "nome": "Maria Exemplo", "cargo": "Supervisora", "empresa": "Condomínio",
        "endereco": "Rua Exemplo", "telefone": "41999990000",
        "contatoEmergenciaNome": "João", "contatoEmergenciaTel": "41988887777"
    })
    assert updated.status_code == 200
    assert updated.json()["contatoEmergenciaNome"] == "João"
    assert client.delete(f"/api/v1/empregados/{item['id']}").status_code == 204


def test_employee_required_fields_and_not_found():
    assert client.post("/api/v1/empregados", json={"nome": "Maria"}).status_code == 422
    assert client.delete("/api/v1/empregados/inexistente").status_code == 404


def test_employees_are_isolated_between_app_instances():
    first, second = TestClient(create_app()), TestClient(create_app())
    created = first.post("/api/v1/empregados", json={"nome": "Pessoa Isolada", "cargo": "Zelador"}).json()
    assert first.get("/api/v1/empregados").json()[0]["id"] == created["id"]
    assert second.get("/api/v1/empregados").json() == []
