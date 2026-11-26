import pytest
from fastapi import HTTPException

from app.core.authorization import (
    CAPABILITIES,
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


def test_admin_is_denied_until_permission_matrix_is_approved() -> None:
    for capability in CAPABILITIES:
        assert not has_capability(principal("Admin"), capability)


def test_operator_is_denied_until_permission_matrix_is_approved() -> None:
    for capability in CAPABILITIES:
        assert not has_capability(principal("Operador"), capability)


@pytest.mark.parametrize("profile", ["admin", "Root", "", "Administrador", ""])
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


def test_require_capability_raises_for_denied_access() -> None:
    with pytest.raises(HTTPException) as error:
        require_capability(principal("Operador"), "financeiro:create")
    assert error.value.status_code == 403
    assert error.value.detail == "Acesso negado para esta operação."


def test_require_capability_denies_admin_until_matrix_is_approved() -> None:
    with pytest.raises(HTTPException) as error:
        require_capability(principal("Admin"), "financeiro:read")
    assert error.value.status_code == 403


def test_non_string_identity_fields_are_denied() -> None:
    malformed = AuthenticatedPrincipal(None, "usuario@example.com", "Admin", "Ativo")
    assert not has_capability(malformed, "dashboard:read")



def test_fastapi_dependency_enforces_capability_after_authentication() -> None:
    from app.core.authorization import require_capability_dependency

    dependency = require_capability_dependency("financeiro:read")
    for profile in ("Admin", "Operador"):
        with pytest.raises(HTTPException) as error:
            dependency(principal(profile))
        assert error.value.status_code == 403


def test_fastapi_dependency_does_not_grant_unapproved_profile() -> None:
    from app.core.authorization import require_capability_dependency

    dependency = require_capability_dependency("dashboard:read")
    with pytest.raises(HTTPException) as error:
        dependency(principal("Admin"))
    assert error.value.status_code == 403
