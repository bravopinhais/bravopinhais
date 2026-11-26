from fastapi.testclient import TestClient

from app.main import create_app
from app.modules.usuarios.schemas import UsuarioInput


def make_client(profile: str = "Admin", email: str = "financeiro-admin@example.com"):
    application = create_app(storage_backend="memory")
    application.state.google_token_verifier = lambda token: {
        "sub": f"google-{email}",
        "email": email,
        "email_verified": True,
    }
    application.state.services.usuarios.create(
        UsuarioInput(
            email=email,
            nome="Usuário Financeiro",
            loja="Bravo Shadow",
            cargo="Gestor",
            perfil=profile,
            status="Ativo",
        )
    )
    return application, TestClient(application)


def headers():
    return {"Authorization": "Bearer token-de-teste"}


def title_payload(value: str = "125.50"):
    return {
        "tipo": "Pagar",
        "planoContaId": "",
        "historico": "Despesa de teste",
        "valor": value,
    }


def test_financeiro_requires_authenticated_identity():
    application = create_app(storage_backend="memory")
    response = TestClient(application).get("/api/v1/financeiro")
    assert response.status_code == 401


def test_operator_cannot_read_financeiro():
    application, client = make_client("Operador", "operador-fin@example.com")
    response = client.get("/api/v1/financeiro", headers=headers())
    assert response.status_code == 403


def test_admin_can_create_and_read_financeiro():
    application, client = make_client()
    created = client.post(
        "/api/v1/financeiro",
        headers=headers(),
        json=title_payload(),
    )
    assert created.status_code == 201
    assert created.headers["etag"] == '"1"'

    listed = client.get("/api/v1/financeiro", headers=headers())
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["id"] == created.json()["id"]


def test_admin_can_update_financeiro_with_current_etag():
    application, client = make_client()
    created = client.post(
        "/api/v1/financeiro",
        headers=headers(),
        json=title_payload(),
    )
    item_id = created.json()["id"]

    updated = client.put(
        f"/api/v1/financeiro/{item_id}",
        headers={**headers(), "If-Match": '"1"'},
        json=title_payload("200.00"),
    )
    assert updated.status_code == 200
    assert updated.headers["etag"] == '"2"'


def test_admin_can_delete_financeiro():
    application, client = make_client()
    created = client.post(
        "/api/v1/financeiro",
        headers=headers(),
        json=title_payload(),
    )
    item_id = created.json()["id"]

    deleted = client.delete(
        f"/api/v1/financeiro/{item_id}",
        headers=headers(),
    )
    assert deleted.status_code == 204
