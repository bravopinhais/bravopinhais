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


def test_employee_text_fields_are_trimmed_without_changing_phone_format():
    response = client.post("/api/v1/empregados", json={
        "nome": "  Maria Exemplo  ", "cargo": "  Zeladora ",
        "empresa": " Condomínio Exemplo ", "endereco": " Rua A, 100 ",
        "telefone": " (41) 99999-0000 ",
        "contatoEmergenciaNome": " João Silva ",
        "contatoEmergenciaTel": " 41988887777 "
    })
    assert response.status_code == 201
    item = response.json()
    assert item["nome"] == "Maria Exemplo"
    assert item["cargo"] == "Zeladora"
    assert item["empresa"] == "Condomínio Exemplo"
    assert item["endereco"] == "Rua A, 100"
    assert item["telefone"] == "(41) 99999-0000"
    assert item["contatoEmergenciaNome"] == "João Silva"
    assert item["contatoEmergenciaTel"] == "41988887777"


def test_employee_required_fields_reject_whitespace_only_values():
    response = client.post("/api/v1/empregados", json={
        "nome": " Maria ", "cargo": "   "
    })
    assert response.status_code == 422


def test_employee_update_trims_optional_fields():
    created = client.post("/api/v1/empregados", json={
        "nome": "Maria", "cargo": "Zeladora"
    }).json()
    response = client.put(f"/api/v1/empregados/{created['id']}", json={
        "nome": " Maria Atualizada ", "cargo": " Supervisora ",
        "empresa": "  ", "endereco": " Rua B "
    })
    assert response.status_code == 200
    assert response.json()["nome"] == "Maria Atualizada"
    assert response.json()["cargo"] == "Supervisora"
    assert response.json()["empresa"] == ""
    assert response.json()["endereco"] == "Rua B"
