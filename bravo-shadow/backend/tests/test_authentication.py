import pytest
from fastapi import HTTPException

from app.core.authentication import principal_from_google_claims
from app.core.storage import build_storage_services
from app.modules.usuarios.schemas import UsuarioInput


def make_user(services, email="admin@example.com", profile="Admin", account_status="Ativo"):
    data = UsuarioInput(
        email=email,
        nome="Administrador",
        loja="Bravo",
        cargo="Gestor",
        perfil=profile,
        status=account_status,
    )
    return services.usuarios.create(data)


def test_google_token_verifier_uses_configured_client_id_as_audience(monkeypatch):
    from app.core.authentication import verify_google_id_token
    from google.oauth2 import id_token

    calls = {}

    def fake_verify(token, request, audience):
        calls.update(token=token, request=request, audience=audience)
        return {"sub": "google-subject"}

    monkeypatch.setenv("GOOGLE_CLIENT_ID", "bravo-client-id.apps.googleusercontent.com")
    monkeypatch.setattr(id_token, "verify_oauth2_token", fake_verify)

    claims = verify_google_id_token("google-id-token")

    assert claims == {"sub": "google-subject"}
    assert calls["token"] == "google-id-token"
    assert calls["audience"] == "bravo-client-id.apps.googleusercontent.com"
    assert calls["request"] is not None


def test_google_token_verifier_fails_closed_without_client_id(monkeypatch):
    from app.core.authentication import verify_google_id_token

    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)

    with pytest.raises(RuntimeError, match="GOOGLE_CLIENT_ID"):
        verify_google_id_token("google-id-token")


def test_verified_google_email_resolves_internal_profile_and_status():
    services = build_storage_services("memory")
    make_user(services)

    principal = principal_from_google_claims(
        {
            "sub": "google-subject-1",
            "email": "ADMIN@example.com",
            "email_verified": True,
        },
        services.usuarios,
    )

    assert principal.subject == "google-subject-1"
    assert principal.email == "admin@example.com"
    assert principal.profile == "Admin"
    assert principal.account_status == "Ativo"


@pytest.mark.parametrize(
    "claims",
    [
        {"sub": "subject", "email": "admin@example.com", "email_verified": False},
        {"sub": "", "email": "admin@example.com", "email_verified": True},
        {"sub": "subject", "email": "", "email_verified": True},
        {"email": "admin@example.com", "email_verified": True},
    ],
)
def test_unverified_or_incomplete_google_claims_are_rejected(claims):
    services = build_storage_services("memory")
    make_user(services)
    with pytest.raises(HTTPException) as error:
        principal_from_google_claims(claims, services.usuarios)
    assert error.value.status_code == 401


def test_unknown_email_is_not_allowed_to_access_bravo():
    services = build_storage_services("memory")
    with pytest.raises(HTTPException) as error:
        principal_from_google_claims(
            {"sub": "subject", "email": "unknown@example.com", "email_verified": True},
            services.usuarios,
        )
    assert error.value.status_code == 403


def test_inactive_internal_user_is_denied_even_with_valid_google_identity():
    services = build_storage_services("memory")
    make_user(services, account_status="Inativo")
    with pytest.raises(HTTPException) as error:
        principal_from_google_claims(
            {"sub": "subject", "email": "admin@example.com", "email_verified": True},
            services.usuarios,
        )
    assert error.value.status_code == 403

def test_ambiguous_duplicate_internal_email_is_denied():
    from types import SimpleNamespace

    class DuplicateUsersService:
        def list(self):
            return [
                SimpleNamespace(email="admin@example.com", status="Ativo", perfil="Admin"),
                SimpleNamespace(email="ADMIN@example.com", status="Ativo", perfil="Operador"),
            ]

    with pytest.raises(HTTPException) as error:
        principal_from_google_claims(
            {"sub": "subject", "email": "admin@example.com", "email_verified": True},
            DuplicateUsersService(),
        )

    assert error.value.status_code == 403
