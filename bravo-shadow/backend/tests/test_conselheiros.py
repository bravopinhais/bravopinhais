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


def test_all_council_routes_require_authentication():
    client = build_client()
    assert client.get("/api/v1/conselheiros").status_code == 401
    assert client.post("/api/v1/conselheiros", json={"nome": "Pessoa", "cargo": "Síndico"}).status_code == 401
    assert client.put("/api/v1/conselheiros/1", json={"nome": "Pessoa", "cargo": "Síndico"}).status_code == 401
    assert client.delete("/api/v1/conselheiros/1").status_code == 401


def test_both_profiles_are_denied_all_council_actions_until_approval():
    for profile in ("Admin", "Operador"):
        client = build_client(profile)
        assert client.get("/api/v1/conselheiros").status_code == 403
        assert client.post("/api/v1/conselheiros", json={"nome": "Pessoa", "cargo": "Síndico"}).status_code == 403
        assert client.put("/api/v1/conselheiros/1", json={"nome": "Pessoa", "cargo": "Síndico"}).status_code == 403
        assert client.delete("/api/v1/conselheiros/1").status_code == 403
