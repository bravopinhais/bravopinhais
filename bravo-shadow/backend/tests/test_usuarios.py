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
        ("PUT", "/api/v1/usuarios/id-teste", {"nome":"Pessoa atualizada"}),
        ("DELETE", "/api/v1/usuarios/id-teste", None),
        ("POST", "/api/v1/usuarios/id-teste/desativar", None),
    ]
    for method, path, payload in requests:
        assert client.request(method, path, json=payload).status_code == 401


def test_both_profiles_are_denied_user_management_until_matrix_approval():
    requests = [
        ("GET", "/api/v1/usuarios", None),
        ("GET", "/api/v1/usuarios/id-teste", None),
        ("POST", "/api/v1/usuarios", {"email":"novo@example.com", "nome":"Pessoa", "cargo":"Conselho"}),
        ("PUT", "/api/v1/usuarios/id-teste", {"nome":"Pessoa atualizada"}),
        ("DELETE", "/api/v1/usuarios/id-teste", None),
        ("POST", "/api/v1/usuarios/id-teste/desativar", None),
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
    with pytest.raises(HTTPException) as delete_error:
        service.delete(user.id)
    assert delete_error.value.status_code == 410
    assert service.get(user.id).id == user.id


def test_user_schema_rejects_local_password_fields_and_normalizes_email():
    user = UsuarioInput(email=" ADMIN@EXAMPLE.COM ", nome=" Admin ", cargo=" Síndico ")
    assert user.email == "admin@example.com"
    with pytest.raises(ValidationError):
        UsuarioInput(email="user@example.com", nome="Pessoa", cargo="Conselho", senhaHash="legacy")

def test_user_payloads_cannot_set_google_identity_or_internal_subject():
    with pytest.raises(ValidationError):
        UsuarioInput(
            email="novo@example.com", nome="Pessoa", cargo="Conselho",
            google_subject="attacker-controlled-subject",
        )

    with pytest.raises(ValidationError):
        UsuarioCadastroInput(
            email="novo@example.com", nome="Pessoa", cargo="Conselho",
            google_subject="attacker-controlled-subject",
        )

    with pytest.raises(ValidationError):
        UsuarioDadosCadastraisUpdateInput(google_subject="replacement-subject")

    with pytest.raises(ValidationError):
        UsuarioDadosCadastraisUpdateInput(subject="replacement-subject")


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
        UsuarioCadastroInput(email="novo@example.com", nome="   ", cargo="Conselho")

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




def test_cadastral_service_cannot_assign_privileged_profile_or_status():
    service = UsuariosService()
    created = service.create_cadastral(
        UsuarioCadastroInput(
            email="novo@example.com", nome="Pessoa", cargo="Conselho"
        )
    )
    assert created.perfil == "Operador"
    assert created.status == "Ativo"

    updated = service.update_cadastral(
        created.id, UsuarioDadosCadastraisUpdateInput(nome="Nome atualizado")
    )
    assert updated.nome == "Nome atualizado"
    assert updated.email == "novo@example.com"
    assert updated.perfil == "Operador"
    assert updated.status == "Ativo"


def test_cadastral_update_preserves_existing_admin_and_inactive_state():
    service = UsuariosService()
    existing = service.create(
        UsuarioInput(
            email="admin@example.com", nome="Admin", cargo="Gestor",
            perfil="Admin", status="Inativo",
        )
    )
    updated = service.update_cadastral(
        existing.id,
        UsuarioDadosCadastraisUpdateInput(cargo="Conselheiro"),
    )
    assert updated.cargo == "Conselheiro"
    assert updated.perfil == "Admin"
    assert updated.status == "Inativo"
    assert updated.email == "admin@example.com"



def test_cadastral_update_rejects_explicit_null_values():
    with pytest.raises(ValidationError):
        UsuarioDadosCadastraisUpdateInput(nome=None, cargo="Conselho")

def test_user_service_rejects_case_insensitive_duplicate_email():
    service = UsuariosService()
    service.create(
        UsuarioInput(
            email="Pessoa@Example.com",
            nome="Pessoa original",
            cargo="Conselho",
        )
    )

    with pytest.raises(HTTPException) as error:
        service.create(
            UsuarioInput(
                email=" PESSOA@example.com ",
                nome="Pessoa duplicada",
                cargo="Conselho",
            )
        )

    assert error.value.status_code == 409
    assert len(service.list()) == 1


def test_user_update_rejects_email_already_owned_by_another_user_case_insensitively():
    service = UsuariosService()
    first = service.create(
        UsuarioInput(email="primeiro@example.com", nome="Primeiro", cargo="Conselho")
    )
    second = service.create(
        UsuarioInput(email="segundo@example.com", nome="Segundo", cargo="Conselho")
    )

    with pytest.raises(HTTPException) as error:
        service.update(
            second.id,
            UsuarioInput(
                email=" PRIMEIRO@EXAMPLE.COM ",
                nome="Segundo atualizado",
                cargo="Conselho",
            ),
        )

    assert error.value.status_code == 409
    assert service.get(first.id).email == "primeiro@example.com"
    assert service.get(second.id).email == "segundo@example.com"


def test_persistent_user_cadastral_mutations_fail_closed_without_actor():
    from app.core.repositories import InMemoryCollectionRepository
    service = UsuariosService(repository=InMemoryCollectionRepository(), audit_sink=object())
    data = UsuarioCadastroInput(email="novo@example.com", nome="Pessoa", cargo="Conselho")
    with pytest.raises(HTTPException) as create_error:
        service.create_cadastral(data)
    assert create_error.value.status_code == 403
    with pytest.raises(HTTPException) as update_error:
        service.update_cadastral("missing", UsuarioDadosCadastraisUpdateInput(nome="Atualizado"))
    assert update_error.value.status_code == 403
    assert service.list() == []


def test_user_cadastral_mutations_emit_audit_events_when_actor_is_present():
    from app.core.repositories import InMemoryCollectionRepository

    class Sink:
        def __init__(self):
            self.events = []
        def append_in_transaction(self, connection, event):
            assert connection is self
            self.events.append(event)

    class AuditedRepository(InMemoryCollectionRepository):
        def add_audited(self, item, *, event, audit_sink):
            self.add(item.id, item)
            audit_sink.append_in_transaction(audit_sink, event)
        def update_cadastral_audited(self, item_id, *, event, audit_sink, **payload):
            current = self.get(item_id)
            if current is None:
                raise HTTPException(status_code=404, detail="Usuário não encontrado.")
            updated = current.model_copy(update=payload)
            self.replace(item_id, updated)
            audit_sink.append_in_transaction(audit_sink, event)
            return updated

    sink = Sink()
    service = UsuariosService(repository=AuditedRepository(), audit_sink=sink)
    actor = AuthenticatedPrincipal("google-subject", "admin@example.com", "Admin", "Ativo")
    created = service.create_cadastral(
        UsuarioCadastroInput(email="novo@example.com", nome="Pessoa", cargo="Conselho"),
        actor=actor, request_id="req-create",
    )
    updated = service.update_cadastral(
        created.id, UsuarioDadosCadastraisUpdateInput(nome="Pessoa Atualizada"),
        actor=actor, request_id="req-update",
    )
    assert updated.nome == "Pessoa Atualizada"
    assert [event.action for event in sink.events] == ["usuarios:create", "usuarios:update_cadastral"]
    assert [event.request_id for event in sink.events] == ["req-create", "req-update"]


def test_user_cadastral_mutations_require_admin_profile_even_with_active_identity():
    from app.core.repositories import InMemoryCollectionRepository
    service = UsuariosService(repository=InMemoryCollectionRepository(), audit_sink=object())
    operator = AuthenticatedPrincipal("operator-subject", "op@example.com", "Operador", "Ativo")
    with pytest.raises(HTTPException) as create_error:
        service.create_cadastral(
            UsuarioCadastroInput(email="novo@example.com", nome="Pessoa", cargo="Conselho"),
            actor=operator,
        )
    assert create_error.value.status_code == 403
    with pytest.raises(HTTPException) as update_error:
        service.update_cadastral(
            "missing", UsuarioDadosCadastraisUpdateInput(nome="Atualizado"),
            actor=operator,
        )
    assert update_error.value.status_code == 403
    assert service.list() == []
