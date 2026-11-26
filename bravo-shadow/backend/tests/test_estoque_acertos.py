from fastapi.testclient import TestClient

from app.main import app, create_app


client = TestClient(app)


def setup_function():
    app.state.services.estoque._items.clear()
    app.state.services.acertos_estoque._items.clear()
    app.state.services.motivos_acerto._items.clear()


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
    deletion = client.delete("/api/v1/acertos-estoque/" + move.json()["id"])
    assert deletion.status_code == 409
    assert client.get("/api/v1/estoque").json()[0]["quantidade"] == 3
    assert client.get("/api/v1/acertos-estoque").json()[0]["id"] == move.json()["id"]


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


def test_adjustment_reason_link_and_restrict_delete():
    product = client.post(
        "/api/v1/estoque", json={"item": "Filtro", "quantidade": 3}
    ).json()
    reason = client.post(
        "/api/v1/motivos-acerto-estoque", json={"nome": "Avaria"}
    ).json()
    movement = client.post(
        "/api/v1/acertos-estoque",
        json={
            "tipo": "Entrada",
            "produtoId": product["id"],
            "quantidade": 1,
            "motivo": "Texto legado",
            "motivoId": reason["id"],
        },
    )
    assert movement.status_code == 201
    data = movement.json()
    assert data["motivoId"] == reason["id"]
    assert data["motivo"] == "Avaria"
    assert client.delete("/api/v1/motivos-acerto-estoque/" + reason["id"]).status_code == 409
    assert client.delete("/api/v1/acertos-estoque/" + data["id"]).status_code == 409
    assert client.delete("/api/v1/motivos-acerto-estoque/" + reason["id"]).status_code == 409


def test_adjustment_rejects_unknown_reason():
    product = client.post(
        "/api/v1/estoque", json={"item": "Filtro", "quantidade": 3}
    ).json()
    response = client.post(
        "/api/v1/acertos-estoque",
        json={
            "tipo": "Entrada",
            "produtoId": product["id"],
            "quantidade": 1,
            "motivo": "Texto",
            "motivoId": "motivo-inexistente",
        },
    )
    assert response.status_code == 404


def test_stock_metadata_is_trimmed_and_registration_date_is_normalized():
    response = client.post(
        "/api/v1/estoque",
        json={
            "item": "  Lâmpada LED  ",
            "marca": "  Marca A ",
            "linha": " Linha 2  ",
            "fabricante": " Fábrica X ",
            "etiqueta": " 789 ",
            "fotoNome": " foto.png ",
            "dataCadastro": " 2026-11-26 ",
            "fotoCompactadaGzip": "  legado compactado  ",
        },
    )
    assert response.status_code == 201
    item = response.json()
    assert item["item"] == "Lâmpada LED"
    assert item["marca"] == "Marca A"
    assert item["linha"] == "Linha 2"
    assert item["fabricante"] == "Fábrica X"
    assert item["etiqueta"] == "789"
    assert item["fotoNome"] == "foto.png"
    assert item["dataCadastro"] == "2026-11-26"
    assert item["fotoCompactadaGzip"] == "  legado compactado  "


def test_stock_item_rejects_whitespace_only_name():
    response = client.post("/api/v1/estoque", json={"item": "   "})
    assert response.status_code == 422


def test_stock_registration_date_rejects_invalid_calendar_date():
    response = client.post(
        "/api/v1/estoque",
        json={"item": "Material", "dataCadastro": "2026-02-30"},
    )
    assert response.status_code == 422


def test_stock_registration_date_accepts_blank_as_not_informed():
    response = client.post(
        "/api/v1/estoque",
        json={"item": "Material", "dataCadastro": "   "},
    )
    assert response.status_code == 201
    assert response.json()["dataCadastro"] == ""


def test_stock_registration_date_rejects_non_iso_format():
    response = client.post(
        "/api/v1/estoque",
        json={"item": "Material", "dataCadastro": "26/11/2026"},
    )
    assert response.status_code == 422


def test_adjustment_trims_required_text_and_optional_reason_id():
    product = client.post("/api/v1/estoque", json={"item": "Filtro", "quantidade": 2}).json()
    reason = client.post("/api/v1/motivos-acerto-estoque", json={"nome": "Avaria"}).json()
    response = client.post(
        "/api/v1/acertos-estoque",
        json={
            "tipo": "Entrada",
            "produtoId": " " + product["id"] + " ",
            "quantidade": 1,
            "motivo": "  Reposição  ",
            "motivoId": " " + reason["id"] + " ",
        },
    )
    assert response.status_code == 201
    assert response.json()["produtoId"] == product["id"]
    assert response.json()["motivo"] == "Avaria"
    assert response.json()["motivoId"] == reason["id"]


def test_adjustment_rejects_blank_product_and_reason_text():
    product = client.post("/api/v1/estoque", json={"item": "Filtro", "quantidade": 2}).json()
    for payload in (
        {"tipo": "Entrada", "produtoId": "   ", "quantidade": 1, "motivo": "Reposição"},
        {"tipo": "Entrada", "produtoId": product["id"], "quantidade": 1, "motivo": "   "},
    ):
        assert client.post("/api/v1/acertos-estoque", json=payload).status_code == 422


def test_adjustment_requires_positive_integer_quantity():
    product = client.post("/api/v1/estoque", json={"item": "Filtro", "quantidade": 2}).json()
    for quantity in (0, -1):
        response = client.post(
            "/api/v1/acertos-estoque",
            json={
                "tipo": "Entrada",
                "produtoId": product["id"],
                "quantidade": quantity,
                "motivo": "Reposição",
            },
        )
        assert response.status_code == 422


def test_adjustment_delete_of_unknown_id_returns_404():
    response = client.delete("/api/v1/acertos-estoque/does-not-exist")
    assert response.status_code == 404
