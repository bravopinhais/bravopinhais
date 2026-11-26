from fastapi.testclient import TestClient

from app.core.authentication import get_current_principal
from app.core.authorization import AuthenticatedPrincipal
from app.main import create_app


def build_client(profile: str | None = None) -> TestClient:
    application = create_app(storage_backend="memory")
    if profile is not None:
        async def authenticated_principal() -> AuthenticatedPrincipal:
            return AuthenticatedPrincipal(
                subject="google-test-subject",
                email="teste@example.com",
                profile=profile,
                account_status="Ativo",
            )
        application.dependency_overrides[get_current_principal] = authenticated_principal
    return TestClient(application)


def test_all_formas_monetarias_routes_require_authentication():
    client = build_client()
    assert client.get("/api/v1/formas-monetarias").status_code == 401
    assert client.post("/api/v1/formas-monetarias", json={"nome": "Boleto"}).status_code == 401
    assert client.put("/api/v1/formas-monetarias/1", json={"nome": "PIX"}).status_code == 401
    assert client.delete("/api/v1/formas-monetarias/1").status_code == 401


def test_admin_is_denied_all_formas_monetarias_actions_until_matrix_approval():
    client = build_client("Admin")
    assert client.get("/api/v1/formas-monetarias").status_code == 403
    assert client.post("/api/v1/formas-monetarias", json={"nome": "Boleto"}).status_code == 403
    assert client.put("/api/v1/formas-monetarias/1", json={"nome": "PIX"}).status_code == 403
    assert client.delete("/api/v1/formas-monetarias/1").status_code == 403


def test_operator_is_denied_all_formas_monetarias_actions_until_matrix_approval():
    client = build_client("Operador")
    assert client.get("/api/v1/formas-monetarias").status_code == 403
    assert client.post("/api/v1/formas-monetarias", json={"nome": "Boleto"}).status_code == 403
    assert client.put("/api/v1/formas-monetarias/1", json={"nome": "PIX"}).status_code == 403
    assert client.delete("/api/v1/formas-monetarias/1").status_code == 403
