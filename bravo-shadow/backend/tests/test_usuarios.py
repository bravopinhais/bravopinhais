import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.authentication import get_current_principal
from app.core.authorization import AuthenticatedPrincipal
from app.main import create_app
from app.modules.usuarios.schemas import UsuarioInput
from app.modules.usuarios.service import UsuariosService


def build_client(profile: str | None = None) -> TestClient:
    application = create_app(storage_backend="memory")
    if profile is not None:
        async def authenticated_principal() -> AuthenticatedPrincipal:
            return AuthenticatedPrincipal(subject="google-test-subject", email="teste@example.com", profile=profile, account_status="Ativo")
        application.dependency_overrides[get_current_principal] = authenticated_principal
    return TestClient(application)


def test_all_user_management_routes_require_authentication():
    client = build_client()
    requests = [
        ("GET", "/api/v1/usuarios", None),
        ("GET", "/api/v1/usuarios/id-teste", None),
        ("POST", "/api/v1/usuarios", {"email":"novo@example.com", "nome":"Pessoa", "cargo":"Conselho"}),
        ("PUT", "/api/v1/usuarios/id-teste", {"email":"novo@example.com", "nome":"Pessoa", "cargo":"Conselho"}),
        ("DELETE", "/api/v1/usuarios/id-teste", None),
    ]
    for method, path, payload in requests:
        assert client.request(method, path, json=payload).status_code == 401


def test_both_profiles_are_denied_user_management_until_matrix_approval():
    requests = [
        ("GET", "/api/v1/usuarios", None),
        ("GET", "/api/v1/usuarios/id-teste", None),
        ("POST", "/api/v1/usuarios", {"email":"novo@example.com", "nome":"Pessoa", "cargo":"Conselho"}),
        ("PUT", "/api/v1/usuarios/id-teste", {"email":"novo@example.com", "nome":"Pessoa", "cargo":"Conselho"}),
        ("DELETE", "/api/v1/usuarios/id-teste", None),
    ]
    for profile in ("Admin", "Operador"):
        client = build_client(profile)
        for method, path, payload in requests:
            assert client.request(method, path, json=payload).status_code == 403


def test_user_service_crud_email_uniqueness_and_status():
    service = UsuariosService()
    data = UsuarioInput(email="  ADMIN@EXAMPLE.COM ", nome="Administrador", cargo="Síndico", perfil="Admin")
    user = service.create(data)
    assert user.email == "admin@example.com"
    with pytest.raises(HTTPException) as error:
        service.create(UsuarioInput(email="admin@example.com", nome="Duplicado", cargo="Conselho"))
    assert error.value.status_code == 409
    updated = service.update(user.id, UsuarioInput(email="admin@example.com", nome="Administrador", cargo="Síndico", perfil="Admin", status="Inativo"))
    assert updated.status == "Inativo"
    service.delete(user.id)
    with pytest.raises(HTTPException):
        service.get(user.id)


def test_user_schema_rejects_local_password_fields_and_normalizes_email():
    user = UsuarioInput(email=" ADMIN@EXAMPLE.COM ", nome=" Admin ", cargo=" Síndico ")
    assert user.email == "admin@example.com"
    with pytest.raises(ValidationError):
        UsuarioInput(email="user@example.com", nome="Pessoa", cargo="Conselho", senhaHash="legacy")
