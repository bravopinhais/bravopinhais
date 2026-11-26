from fastapi.testclient import TestClient

from app.main import app, create_app


client = TestClient(app)


def setup_function():
    app.state.services.categorias._items.clear()
    app.state.services.motivos_acerto._items.clear()


def test_categories_crud():
    created = client.post("/api/v1/categorias", json={"nome": "Financeiro"})
    assert created.status_code == 201
    item = created.json()
    assert client.get("/api/v1/categorias").json()[0]["nome"] == "Financeiro"
    assert client.delete("/api/v1/categorias/" + item["id"]).status_code == 204
    assert client.delete("/api/v1/categorias/" + item["id"]).status_code == 404


def test_adjustment_reasons_crud():
    created = client.post("/api/v1/motivos-acerto-estoque", json={"nome": "Quebra"})
    assert created.status_code == 201
    item = created.json()
    assert client.get("/api/v1/motivos-acerto-estoque").json()[0]["nome"] == "Quebra"
    assert client.delete("/api/v1/motivos-acerto-estoque/" + item["id"]).status_code == 204


def test_names_are_required():
    assert client.post("/api/v1/categorias", json={"nome": ""}).status_code == 422
    assert client.post("/api/v1/motivos-acerto-estoque", json={}).status_code == 422


def test_catalog_services_are_isolated_between_app_instances():
    first = TestClient(create_app())
    second = TestClient(create_app())

    category = first.post("/api/v1/categorias", json={"nome": "Documentos"}).json()
    reason = first.post("/api/v1/motivos-acerto-estoque", json={"nome": "Avaria"}).json()

    assert first.get("/api/v1/categorias").json()[0]["id"] == category["id"]
    assert first.get("/api/v1/motivos-acerto-estoque").json()[0]["id"] == reason["id"]
    assert second.get("/api/v1/categorias").json() == []
    assert second.get("/api/v1/motivos-acerto-estoque").json() == []
