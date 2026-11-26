import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.authentication import get_current_principal
from app.core.authorization import AuthenticatedPrincipal
from app.main import create_app
from app.modules.usuarios.schemas import (
    UsuarioInput, UsuarioCadastroInput,
    UsuarioDadosCadastraisUpdateInput, UsuarioAdministracaoInput,
)
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

def test_concurrent_user_creation_cannot_duplicate_email_in_memory():
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    service = UsuariosService()
    barrier = Barrier(8)

    def create_same_email(index):
        barrier.wait()
        try:
            service.create(
                UsuarioInput(
                    email="same@example.com",
                    nome=f"Pessoa {index}",
                    cargo="Conselho",
                )
            )
            return "created"
        except HTTPException as error:
            return error.status_code

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(create_same_email, range(8)))

    assert results.count("created") == 1
    assert results.count(409) == 7
    assert len(service.list()) == 1

def test_separated_user_schemas_keep_privileged_fields_out_of_cadastral_payloads():
    cadastro = UsuarioCadastroInput(
        email=" NOVO@EXAMPLE.COM ", nome=" Pessoa ", cargo="Conselho"
    )
    assert cadastro.email == "novo@example.com"
    assert cadastro.nome == "Pessoa"

    with pytest.raises(ValidationError):
        UsuarioCadastroInput(
            email="novo@example.com", nome="Pessoa", cargo="Conselho",
            perfil="Admin",
        )

    update = UsuarioDadosCadastraisUpdateInput(nome=" Nome novo ")
    assert update.nome == "Nome novo"
    with pytest.raises(ValidationError):
        UsuarioDadosCadastraisUpdateInput(email="troca@example.com")
    with pytest.raises(ValidationError):
        UsuarioDadosCadastraisUpdateInput(status="Inativo")


def test_cadastral_update_requires_at_least_one_non_empty_field():
    with pytest.raises(ValidationError):
        UsuarioDadosCadastraisUpdateInput()
    with pytest.raises(ValidationError):
        UsuarioDadosCadastraisUpdateInput(nome="   ")


def test_administrative_user_schema_requires_explicit_profile_and_status():
    change = UsuarioAdministracaoInput(perfil="Operador", status="Inativo")
    assert change.perfil == "Operador"
    assert change.status == "Inativo"
    with pytest.raises(ValidationError):
        UsuarioAdministracaoInput(perfil="Admin")
    with pytest.raises(ValidationError):
        UsuarioAdministracaoInput(perfil="Root", status="Ativo")

