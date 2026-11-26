import pytest
from fastapi import HTTPException

from app.core.authentication import principal_from_google_claims
from app.core.storage import build_storage_services


def make_user(services, email="admin@example.com", profile="Admin", account_status="Ativo"):
    return services.usuarios.create({
        "email": email,
        "nome": "Administrador",
        "loja": "Bravo",
        "cargo": "Gestor",
        "perfil": profile,
        "status": account_status,
    })


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
