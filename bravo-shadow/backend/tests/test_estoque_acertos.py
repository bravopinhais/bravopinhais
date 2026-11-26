from fastapi.testclient import TestClient

from app.main import app, create_app


client = TestClient(app)


def setup_function():
    app.state.services.estoque._items.clear()
    app.state.services.acertos_estoque._items.clear()


def test_stock_crud_and_extended_origin_fields():
    response = client.post(
        "/api/v1/estoque",
        json={
            "item": "Lâmpada LED",
            "quantidade": 5,
            "minimo": 2,
            "maximo": 10,
            "etiqueta": "789",
            "marca": "Marca A",
            "linha": "LED",
            "fabricante": "Fábrica X",
            "dataCadastro": "2026-11-26",
        },
    )
    assert response.status_code == 201
    item = response.json()
    assert item["marca"] == "Marca A" and item["fabricante"] == "Fábrica X"
    assert client.put(
        "/api/v1/estoque/" + item["id"],
        json={
            "item": "Lâmpada LED 9W",
            "quantidade": 4,
            "minimo": 2,
            "maximo": 10,
            "etiqueta": "789",
        },
    ).status_code == 200
    assert client.delete("/api/v1/estoque/" + item["id"]).status_code == 204


def test_adjustment_updates_quantity_and_prevents_negative_balance():
    product = client.post(
        "/api/v1/estoque", json={"item": "Cabo", "quantidade": 5}
    ).json()
    move = client.post(
        "/api/v1/acertos-estoque",
        json={
            "tipo": "Saída",
            "produtoId": product["id"],
            "quantidade": 2,
            "motivo": "Uso interno",
        },
    )
    assert move.status_code == 201
    assert client.get("/api/v1/estoque").json()[0]["quantidade"] == 3
    assert (
        client.post(
            "/api/v1/acertos-estoque",
            json={
                "tipo": "Saída",
                "produtoId": product["id"],
                "quantidade": 4,
                "motivo": "Uso",
            },
        ).status_code
        == 409
    )
    assert client.delete("/api/v1/acertos-estoque/" + move.json()["id"]).status_code == 204
    assert client.get("/api/v1/estoque").json()[0]["quantidade"] == 3


def test_adjustment_requires_existing_product():
    response = client.post(
        "/api/v1/acertos-estoque",
        json={
            "tipo": "Entrada",
            "produtoId": "missing",
            "quantidade": 1,
            "motivo": "Teste",
        },
    )
    assert response.status_code == 404


def test_inventory_and_adjustments_are_isolated_between_app_instances():
    first = TestClient(create_app())
    second = TestClient(create_app())

    product = first.post(
        "/api/v1/estoque", json={"item": "Material isolado", "quantidade": 8}
    ).json()
    movement = first.post(
        "/api/v1/acertos-estoque",
        json={
            "tipo": "Saída",
            "produtoId": product["id"],
            "quantidade": 3,
            "motivo": "Consumo",
        },
    )
    assert movement.status_code == 201
    assert first.get("/api/v1/estoque").json()[0]["quantidade"] == 5
    assert second.get("/api/v1/estoque").json() == []
    assert second.get("/api/v1/acertos-estoque").json() == []
    assert first.get("/api/v1/acertos-estoque").json()[0]["produtoId"] == product["id"]
