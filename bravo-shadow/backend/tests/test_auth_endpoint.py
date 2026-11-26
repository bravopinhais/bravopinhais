from fastapi.testclient import TestClient

from app.main import create_app
from app.modules.usuarios.schemas import UsuarioInput


def test_auth_me_requires_bearer_token():
    client = TestClient(create_app(storage_backend="memory"))
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_auth_me_accepts_verified_google_identity_and_internal_active_user():
    application = create_app(storage_backend="memory")
    application.state.google_token_verifier = lambda token: {
        "sub": "google-123",
        "email": "admin@example.com",
        "email_verified": True,
    }
    application.state.services.usuarios.create(
        UsuarioInput(
            email="admin@example.com",
            nome="Admin de teste",
            loja="Bravo Shadow",
            cargo="Gestor",
            perfil="Admin",
            status="Ativo",
        )
    )

    client = TestClient(application)
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer token-de-teste"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "subject": "google-123",
        "email": "admin@example.com",
        "profile": "Admin",
        "status": "Ativo",
    }


def test_auth_me_denies_unknown_google_email():
    application = create_app(storage_backend="memory")
    application.state.google_token_verifier = lambda token: {
        "sub": "google-456",
        "email": "unknown@example.com",
        "email_verified": True,
    }
    response = TestClient(application).get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer token-de-teste"},
    )
    assert response.status_code == 403


def test_auth_me_denies_invalid_google_token():
    application = create_app(storage_backend="memory")

    def reject(token):
        raise ValueError("invalid token")

    application.state.google_token_verifier = reject
    response = TestClient(application).get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer token-invalido"},
    )
    assert response.status_code == 401
