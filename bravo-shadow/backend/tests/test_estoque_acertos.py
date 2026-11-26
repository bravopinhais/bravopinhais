import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from types import MappingProxyType

from app.core.authentication import get_current_principal
from app.core.authorization import AuthenticatedPrincipal, CAPABILITIES
from app.core import authorization
from app.modules.motivos_acerto.schemas import MotivoAcertoInput
from app.main import app, create_app


def configure_test_auth(application):
    async def authenticated_admin():
        return AuthenticatedPrincipal(
            subject="google-test-subject",
            email="teste@example.com",
            profile="Admin",
            account_status="Ativo",
        )
    application.dependency_overrides[get_current_principal] = authenticated_admin


@pytest.fixture(autouse=True)
def allow_test_admin(monkeypatch):
    monkeypatch.setattr(
        authorization,
        "ROLE_CAPABILITIES",
        MappingProxyType({"Admin": CAPABILITIES, "Operador": frozenset()}),
    )
    configure_test_auth(app)
    yield
    app.dependency_overrides.clear()


client = TestClient(app)


def setup_function():
    app.state.services.estoque._items.clear()
    app.state.services.acertos_estoque._items.clear()
    app.state.services.motivos_acerto._items.clear()


def test_stock_crud_and_extended_origin_fields():
    response = client.post(
        "/api/v1/estoque",
        json={
            "item": "Lâmpada LED", "quantidade": 5, "minimo": 2, "maximo": 10,
            "etiqueta": "789", "marca": "Marca A", "linha": "LED",
            "fabricante": "Fábrica X", "dataCadastro": "2026-11-26",
        },
    )
    assert response.status_code == 201
    item = response.json()
    assert item["marca"] == "Marca A" and item["fabricante"] == "Fábrica X"
    assert client.put(
        "/api/v1/estoque/" + item["id"],
        json={"item": "Lâmpada LED 9W", "quantidade": 4, "minimo": 2, "maximo": 10, "etiqueta": "789"},
    ).status_code == 200
    assert client.delete("/api/v1/estoque/" + item["id"]).status_code == 204


def test_adjustment_updates_quantity_and_prevents_negative_balance():
    product = client.post("/api/v1/estoque", json={"item": "Cabo", "quantidade": 5}).json()
    move = client.post("/api/v1/acertos-estoque", json={
        "tipo": "Saída", "produtoId": product["id"], "quantidade": 2, "motivo": "Uso interno",
    })
    assert move.status_code == 201
    assert client.get("/api/v1/estoque").json()[0]["quantidade"] == 3
    assert client.post("/api/v1/acertos-estoque", json={
        "tipo": "Saída", "produtoId": product["id"], "quantidade": 4, "motivo": "Uso",
    }).status_code == 409
    # Movimentações são imutáveis pela API; correções devem ocorrer por novo acerto.
    assert client.delete("/api/v1/acertos-estoque/" + move.json()["id"]).status_code == 405
    assert client.get("/api/v1/estoque").json()[0]["quantidade"] == 3
    assert client.get("/api/v1/acertos-estoque").json()[0]["id"] == move.json()["id"]


def test_adjustment_requires_existing_product():
    response = client.post("/api/v1/acertos-estoque", json={
        "tipo": "Entrada", "produtoId": "missing", "quantidade": 1, "motivo": "Teste",
    })
    assert response.status_code == 404


def test_inventory_and_adjustments_are_isolated_between_app_instances():
    first, second = create_app(), create_app()
    configure_test_auth(first)
    configure_test_auth(second)
    first_client, second_client = TestClient(first), TestClient(second)
    product = first_client.post("/api/v1/estoque", json={
        "item": "Material isolado", "quantidade": 8,
    }).json()
    movement = first_client.post("/api/v1/acertos-estoque", json={
        "tipo": "Saída", "produtoId": product["id"], "quantidade": 3, "motivo": "Consumo",
    })
    assert movement.status_code == 201
    assert first_client.get("/api/v1/estoque").json()[0]["quantidade"] == 5
    assert second_client.get("/api/v1/estoque").json() == []
    assert second_client.get("/api/v1/acertos-estoque").json() == []
    assert first_client.get("/api/v1/acertos-estoque").json()[0]["produtoId"] == product["id"]


def test_adjustment_reason_link_and_restrict_delete():
    product = client.post("/api/v1/estoque", json={"item": "Filtro", "quantidade": 3}).json()
    reason = app.state.services.motivos_acerto.create(MotivoAcertoInput(nome="Avaria"))
    movement = client.post("/api/v1/acertos-estoque", json={
        "tipo": "Entrada", "produtoId": product["id"], "quantidade": 1,
        "motivo": "Texto legado", "motivoId": reason.id,
    })
    assert movement.status_code == 201
    data = movement.json()
    assert data["motivoId"] == reason.id and data["motivo"] == "Avaria"
    with pytest.raises(HTTPException) as error:
        app.state.services.motivos_acerto.delete(reason.id)
    assert error.value.status_code == 409
    assert client.delete("/api/v1/acertos-estoque/" + data["id"]).status_code == 405


def test_adjustment_rejects_unknown_reason():
    product = client.post("/api/v1/estoque", json={"item": "Filtro", "quantidade": 3}).json()
    response = client.post("/api/v1/acertos-estoque", json={
        "tipo": "Entrada", "produtoId": product["id"], "quantidade": 1,
        "motivo": "Texto", "motivoId": "motivo-inexistente",
    })
    assert response.status_code == 404


def test_stock_metadata_is_trimmed_and_registration_date_is_normalized():
    response = client.post("/api/v1/estoque", json={
        "item": "  Lâmpada LED  ", "marca": "  Marca A ", "linha": " Linha 2  ",
        "fabricante": " Fábrica X ", "etiqueta": " 789 ", "fotoNome": " foto.png ",
        "dataCadastro": " 2026-11-26 ", "fotoCompactadaGzip": "  legado compactado  ",
    })
    assert response.status_code == 201
    item = response.json()
    assert item["item"] == "Lâmpada LED"
    assert item["marca"] == "Marca A" and item["linha"] == "Linha 2"
    assert item["fabricante"] == "Fábrica X" and item["etiqueta"] == "789"
    assert item["fotoNome"] == "foto.png" and item["dataCadastro"] == "2026-11-26"
    assert item["fotoCompactadaGzip"] == "  legado compactado  "


def test_stock_item_rejects_whitespace_only_name():
    assert client.post("/api/v1/estoque", json={"item": "   "}).status_code == 422


def test_stock_registration_date_rejects_invalid_calendar_date():
    assert client.post("/api/v1/estoque", json={
        "item": "Material", "dataCadastro": "2026-02-30",
    }).status_code == 422


def test_stock_registration_date_accepts_blank_as_not_informed():
    response = client.post("/api/v1/estoque", json={"item": "Material", "dataCadastro": "   "})
    assert response.status_code == 201
    assert response.json()["dataCadastro"] == ""


def test_stock_registration_date_rejects_non_iso_format():
    assert client.post("/api/v1/estoque", json={
        "item": "Material", "dataCadastro": "26/11/2026",
    }).status_code == 422


def test_adjustment_trims_required_text_and_optional_reason_id():
    product = client.post("/api/v1/estoque", json={"item": "Filtro", "quantidade": 2}).json()
    reason = app.state.services.motivos_acerto.create(MotivoAcertoInput(nome="Avaria"))
    response = client.post("/api/v1/acertos-estoque", json={
        "tipo": "Entrada", "produtoId": " " + product["id"] + " ",
        "quantidade": 1, "motivo": "  Reposição  ", "motivoId": " " + reason.id + " ",
    })
    assert response.status_code == 201
    assert response.json()["produtoId"] == product["id"]
    assert response.json()["motivo"] == "Avaria" and response.json()["motivoId"] == reason.id


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
        response = client.post("/api/v1/acertos-estoque", json={
            "tipo": "Entrada", "produtoId": product["id"], "quantidade": quantity,
            "motivo": "Reposição",
        })
        assert response.status_code == 422


def test_adjustment_delete_of_unknown_id_is_not_exposed():
    assert client.delete("/api/v1/acertos-estoque/does-not-exist").status_code == 405


def test_product_with_movements_cannot_be_deleted_or_have_balance_edited():
    product = client.post("/api/v1/estoque", json={"item": "Cabo", "quantidade": 5}).json()
    movement = client.post("/api/v1/acertos-estoque", json={
        "tipo": "Saída", "produtoId": product["id"], "quantidade": 1, "motivo": "Uso",
    })
    assert movement.status_code == 201
    update = client.put("/api/v1/estoque/" + product["id"], json={"item": "Cabo", "quantidade": 9})
    assert update.status_code == 409
    assert client.delete("/api/v1/estoque/" + product["id"]).status_code == 409
    assert client.get("/api/v1/estoque").json()[0]["quantidade"] == 4
    assert len(client.get("/api/v1/acertos-estoque").json()) == 1


def test_product_metadata_can_be_edited_without_changing_movement_balance():
    product = client.post("/api/v1/estoque", json={"item": "Cabo", "quantidade": 5}).json()
    movement = client.post("/api/v1/acertos-estoque", json={
        "tipo": "Saída", "produtoId": product["id"], "quantidade": 1, "motivo": "Uso",
    })
    assert movement.status_code == 201
    update = client.put("/api/v1/estoque/" + product["id"], json={
        "item": "Cabo reforçado", "quantidade": 4, "marca": "Marca B",
    })
    assert update.status_code == 200
    assert update.json()["item"] == "Cabo reforçado"
    assert update.json()["quantidade"] == 4


def test_stock_and_adjustment_routes_require_authentication():
    unauthenticated = TestClient(create_app(storage_backend="memory"))
    assert unauthenticated.get("/api/v1/estoque").status_code == 401
    assert unauthenticated.post("/api/v1/estoque", json={"item": "Teste"}).status_code == 401
    assert unauthenticated.put("/api/v1/estoque/x", json={"item": "Teste"}).status_code == 401
    assert unauthenticated.delete("/api/v1/estoque/x").status_code == 401
    assert unauthenticated.get("/api/v1/acertos-estoque").status_code == 401
    assert unauthenticated.post("/api/v1/acertos-estoque", json={
        "tipo": "Entrada", "produtoId": "x", "quantidade": 1, "motivo": "Teste",
    }).status_code == 401


def test_stock_and_adjustment_routes_deny_profiles_until_matrix_approval(monkeypatch):
    monkeypatch.setattr(
        authorization,
        "ROLE_CAPABILITIES",
        MappingProxyType({"Admin": frozenset(), "Operador": frozenset()}),
    )
    for profile in ("Admin", "Operador"):
        application = create_app(storage_backend="memory")

        async def principal(profile=profile):
            return AuthenticatedPrincipal(
                subject="google-test-subject", email="teste@example.com",
                profile=profile, account_status="Ativo",
            )

        application.dependency_overrides[get_current_principal] = principal
        denied = TestClient(application)
        assert denied.get("/api/v1/estoque").status_code == 403
        assert denied.post("/api/v1/estoque", json={"item": "Teste"}).status_code == 403
        assert denied.put("/api/v1/estoque/x", json={"item": "Teste"}).status_code == 403
        assert denied.delete("/api/v1/estoque/x").status_code == 403
        assert denied.get("/api/v1/acertos-estoque").status_code == 403
        assert denied.post("/api/v1/acertos-estoque", json={
            "tipo": "Entrada", "produtoId": "x", "quantidade": 1, "motivo": "Teste",
        }).status_code == 403
