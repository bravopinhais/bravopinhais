import pytest
from fastapi import HTTPException

from app.core.authorization import (
    CAPABILITIES,
    OPERATOR_CAPABILITIES,
    AuthenticatedPrincipal,
    has_capability,
    require_capability,
)


def principal(profile: str = "Admin", account_status: str = "Ativo") -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(
        subject="google-subject-123",
        email="usuario@example.com",
        profile=profile,
        account_status=account_status,
    )


def test_admin_receives_every_registered_capability():
    for capability in CAPABILITIES:
        assert has_capability(principal("Admin"), capability)


def test_operator_receives_only_approved_operational_capabilities():
    assert OPERATOR_CAPABILITIES
    for capability in CAPABILITIES:
        assert has_capability(principal("Operador"), capability) == (
            capability in OPERATOR_CAPABILITIES
        )


@pytest.mark.parametrize(
    "capability",
    [
        "usuarios:read", "usuarios:create", "usuarios:update",
        "usuarios:delete", "usuarios:deactivate", "condominio:update",
        "plano_contas:create", "plano_contas:update", "plano_contas:delete",
        "formas_monetarias:create", "formas_monetarias:update",
        "formas_monetarias:delete", "contas_bancarias:create",
        "contas_bancarias:update", "contas_bancarias:delete",
        "categorias:create", "categorias:delete",
        "motivos_estoque:create", "motivos_estoque:delete",
        "conselheiros:create", "conselheiros:update", "conselheiros:delete",
    ],
)
def test_operator_cannot_administer_users_or_change_settings(capability):
    assert not has_capability(principal("Operador"), capability)


@pytest.mark.parametrize("profile", ["admin", "Root", "", "Administrador"])
def test_unknown_or_malformed_profiles_are_denied(profile: str) -> None:
    assert not has_capability(principal(profile), "dashboard:read")


def test_inactive_account_is_denied_even_for_admin() -> None:
    assert not has_capability(principal(account_status="Inativo"), "dashboard:read")


def test_missing_identity_is_denied() -> None:
    assert not has_capability(None, "dashboard:read")


def test_empty_subject_or_email_is_denied() -> None:
    missing_subject = AuthenticatedPrincipal("", "usuario@example.com", "Admin", "Ativo")
    missing_email = AuthenticatedPrincipal("subject", " ", "Admin", "Ativo")
    assert not has_capability(missing_subject, "dashboard:read")
    assert not has_capability(missing_email, "dashboard:read")


def test_unknown_capability_is_denied() -> None:
    assert not has_capability(principal(), "financeiro:superuser")


def test_require_capability_raises_for_operator_user_administration():
    with pytest.raises(HTTPException) as error:
        require_capability(principal("Operador"), "usuarios:read")
    assert error.value.status_code == 403
    assert error.value.detail == "Acesso negado para esta operação."


def test_admin_can_manage_users():
    require_capability(principal("Admin"), "usuarios:read")


def test_fastapi_dependency_enforces_capability_after_authentication():
    from app.core.authorization import require_capability_dependency

    dependency = require_capability_dependency("usuarios:read")
    with pytest.raises(HTTPException) as error:
        dependency(principal("Operador"))
    assert error.value.status_code == 403
    assert dependency(principal("Admin")) == principal("Admin")


@pytest.mark.parametrize("profile", [None, [], {}])
def test_non_string_profiles_are_denied_without_raising(profile) -> None:
    malformed = AuthenticatedPrincipal(
        "google-subject-123", "usuario@example.com", profile, "Ativo"
    )
    assert not has_capability(malformed, "dashboard:read")


@pytest.mark.parametrize("capability", [None, [], {}])
def test_non_string_capabilities_are_denied_without_raising(capability) -> None:
    assert not has_capability(principal(), capability)
