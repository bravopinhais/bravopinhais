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


def test_penalty_preserves_legacy_unbounded_numeric_behavior():
    # O HTML original aceita valores numéricos sem min/max; não impor limites novos.
    for value in (-0.01, 100.01):
        response = client.post(
            "/api/v1/formas-monetarias",
            json={"nome": "Teste", "multaPct": value},
        )
        assert response.status_code == 201
        assert response.json()["multaPct"] == value


def test_name_has_no_new_maximum_length_restriction():
    name = "x" * 150
    response = client.post(
        "/api/v1/formas-monetarias",
        json={"nome": name},
    )
    assert response.status_code == 201
    assert response.json()["nome"] == name
