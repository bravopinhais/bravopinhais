from fastapi.testclient import TestClient
from app.main import app
from app.modules.empregados.service import empregados_service

client = TestClient(app)

def setup_function() -> None:
    empregados_service._items.clear()

def test_employee_crud_and_optional_fields():
    response = client.post("/api/v1/empregados", json={"nome":"Maria Exemplo","cargo":"Zeladora"})
    assert response.status_code == 201
    item = response.json()
    assert item["empresa"] == ""
    assert item["contatoEmergenciaTel"] == ""
    updated = client.put(f"/api/v1/empregados/{item['id']}", json={
        "nome":"Maria Exemplo","cargo":"Supervisora","empresa":"Condomínio",
        "endereco":"Rua Exemplo","telefone":"41999990000",
        "contatoEmergenciaNome":"João","contatoEmergenciaTel":"41988887777"
    })
    assert updated.status_code == 200
    assert updated.json()["contatoEmergenciaNome"] == "João"
    assert client.delete(f"/api/v1/empregados/{item['id']}").status_code == 204

def test_employee_required_fields_and_not_found():
    assert client.post("/api/v1/empregados", json={"nome":"Maria"}).status_code == 422
    assert client.delete("/api/v1/empregados/inexistente").status_code == 404
