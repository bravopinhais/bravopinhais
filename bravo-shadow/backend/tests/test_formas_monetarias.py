from fastapi.testclient import TestClient

from app.main import app
from app.modules.formas_monetarias.service import formas_monetarias_service

client = TestClient(app)


def setup_function() -> None:
    formas_monetarias_service._items.clear()


def test_create_list_update_delete_form():
    created = client.post("/api/v1/formas-monetarias", json={"nome": "Boleto", "multaPct": 2.0})
    assert created.status_code == 201
    item = created.json()
    assert item["multaPct"] == 2.0
    updated = client.put(
        f"/api/v1/formas-monetarias/{item['id']}",
        json={"nome": "PIX", "multaPct": 0.0},
    )
    assert updated.status_code == 200
    assert updated.json()["nome"] == "PIX"
    assert client.delete(f"/api/v1/formas-monetarias/{item['id']}").status_code == 204
    assert client.get("/api/v1/formas-monetarias").json() == []


def test_default_penalty_and_missing_update():
    created = client.post("/api/v1/formas-monetarias", json={"nome": "Dinheiro"})
    assert created.status_code == 201
    assert created.json()["multaPct"] == 2.0
    assert client.put("/api/v1/formas-monetarias/unknown", json={"nome": "Teste"}).status_code == 404


def test_name_is_required_and_trimmed():
    assert client.post("/api/v1/formas-monetarias", json={"nome": ""}).status_code == 422
    assert client.post("/api/v1/formas-monetarias", json={"nome": "   "}).status_code == 422
    created = client.post("/api/v1/formas-monetarias", json={"nome": "  PIX  "})
    assert created.status_code == 201
    assert created.json()["nome"] == "PIX"


def test_penalty_must_be_between_zero_and_one_hundred():
    for value in (-0.01, 100.01):
        response = client.post(
            "/api/v1/formas-monetarias",
            json={"nome": "Teste", "multaPct": value},
        )
        assert response.status_code == 422

    for value in (0, 100):
        response = client.post(
            "/api/v1/formas-monetarias",
            json={"nome": "Limite", "multaPct": value},
        )
        assert response.status_code == 201


def test_name_cannot_exceed_one_hundred_characters():
    response = client.post(
        "/api/v1/formas-monetarias",
        json={"nome": "x" * 101},
    )
    assert response.status_code == 422
