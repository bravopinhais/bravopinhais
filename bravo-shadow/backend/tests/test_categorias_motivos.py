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


def test_category_and_reason_routes_require_authentication():
    client = build_client()
    requests = [
        ("GET", "/api/v1/categorias", None),
        ("POST", "/api/v1/categorias", {"nome": "Financeiro"}),
        ("DELETE", "/api/v1/categorias/1", None),
        ("GET", "/api/v1/motivos-acerto-estoque", None),
        ("POST", "/api/v1/motivos-acerto-estoque", {"nome": "Quebra"}),
        ("DELETE", "/api/v1/motivos-acerto-estoque/1", None),
    ]
    for method, path, payload in requests:
        response = client.request(method, path, json=payload)
        assert response.status_code == 401, (method, path, response.text)


def test_category_and_reason_routes_deny_both_profiles_until_approval():
    requests = [
        ("GET", "/api/v1/categorias", None),
        ("POST", "/api/v1/categorias", {"nome": "Financeiro"}),
        ("DELETE", "/api/v1/categorias/1", None),
        ("GET", "/api/v1/motivos-acerto-estoque", None),
        ("POST", "/api/v1/motivos-acerto-estoque", {"nome": "Quebra"}),
        ("DELETE", "/api/v1/motivos-acerto-estoque/1", None),
    ]
    for profile in ("Admin", "Operador"):
        client = build_client(profile)
        for method, path, payload in requests:
            response = client.request(method, path, json=payload)
            assert response.status_code == 403, (profile, method, path, response.text)
