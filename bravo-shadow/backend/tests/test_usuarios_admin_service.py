import pytest
from fastapi import HTTPException

from app.core.authorization import AuthenticatedPrincipal
from app.modules.usuarios.schemas import Usuario, UsuarioAdministracaoInput, UsuarioInput
from app.modules.usuarios.service import UsuariosService


class TransactionalRepository:
    def __init__(self, user):
        self.user = user
        self.call = None

    def get(self, item_id):
        return self.user if item_id == self.user.id else None

    def update_administrative_state(self, item_id, **kwargs):
        self.call = (item_id, kwargs)


def user(email="target@example.com"):
    return Usuario(
        id="usr_target", email=email, nome="Pessoa", loja="Bravo",
        cargo="Conselho", perfil="Admin", status="Ativo",
    )


def test_service_delegates_admin_change_with_bound_audit_event():
    repository = TransactionalRepository(user())
    service = UsuariosService(repository=repository)

    service.update_administrative_state(
        "usr_target",
        UsuarioAdministracaoInput(perfil="Operador", status="Inativo"),
        actor=AuthenticatedPrincipal(subject="google-subject-admin", email="admin@example.com", profile="Admin", account_status="Ativo"),
        audit_sink=object(),
    )

    item_id, kwargs = repository.call
    assert item_id == "usr_target"
    assert kwargs["perfil"] == "Operador"
    assert kwargs["status"] == "Inativo"
    assert kwargs["event"].actor_subject == "google-subject-admin"
    assert kwargs["event"].action == "usuarios:update_administracao"
    assert kwargs["event"].entity_type == "usuario"
    assert kwargs["event"].entity_id == "usr_target"
    assert kwargs["audit_sink"] is not None


def test_service_blocks_actor_from_changing_own_profile_or_status():
    repository = TransactionalRepository(user("ADMIN@example.com"))
    service = UsuariosService(repository=repository)

    with pytest.raises(HTTPException) as error:
        service.update_administrative_state(
            "usr_target",
            UsuarioAdministracaoInput(perfil="Operador", status="Inativo"),
            actor=AuthenticatedPrincipal(subject="google-subject-admin", email=" admin@example.com ", profile="Admin", account_status="Ativo"),
            audit_sink=object(),
        )

    assert error.value.status_code == 403
    assert repository.call is None


def test_memory_repository_fails_closed_for_admin_changes():
    service = UsuariosService()
    created = service.create(
        UsuarioInput(
            email="target@example.com", nome="Pessoa", cargo="Conselho",
            perfil="Admin",
        )
    )

    with pytest.raises(HTTPException) as error:
        service.update_administrative_state(
            created.id,
            UsuarioAdministracaoInput(perfil="Operador", status="Inativo"),
            actor=AuthenticatedPrincipal(subject="google-subject-admin", email="admin@example.com", profile="Admin", account_status="Ativo"),
            audit_sink=object(),
        )

    assert error.value.status_code == 503
    assert service.get(created.id).perfil == "Admin"
    assert service.get(created.id).status == "Ativo"



@pytest.mark.parametrize(
    ("actor_subject", "actor_email"),
    [
        ("", "admin@example.com"),
        ("google-subject-admin", ""),
        ("   ", "admin@example.com"),
    ],
)
def test_service_rejects_missing_authenticated_actor_identity(actor_subject, actor_email):
    repository = TransactionalRepository(user())
    service = UsuariosService(repository=repository)

    with pytest.raises(HTTPException) as error:
        service.update_administrative_state(
            "usr_target",
            UsuarioAdministracaoInput(perfil="Operador", status="Inativo"),
            actor_subject=actor_subject,
            actor_email=actor_email,
            audit_sink=object(),
        )

    assert error.value.status_code == 401
    assert repository.call is None



class DeactivationRepository:
    def __init__(self, user):
        self.user = user
        self.call = None

    def get(self, item_id):
        return self.user if item_id == self.user.id else None

    def deactivate_user(self, item_id, **kwargs):
        self.call = (item_id, kwargs)


class TransactionalAuditSink:
    def append_in_transaction(self, connection, event):
        raise AssertionError("O serviço apenas injeta o sink; o repositório controla a transação.")


def test_service_deactivates_another_user_with_bound_audit_event():
    repository = DeactivationRepository(user())
    sink = TransactionalAuditSink()
    service = UsuariosService(repository=repository, audit_sink=sink)

    service.deactivate(
        "usr_target",
        actor=AuthenticatedPrincipal(subject="google-subject-admin", email="admin@example.com", profile="Admin", account_status="Ativo"),
        request_id="req_0123456789abcdef0123456789abcdef",
    )

    item_id, kwargs = repository.call
    assert item_id == "usr_target"
    assert kwargs["event"].actor_subject == "google-subject-admin"
    assert kwargs["event"].action == "usuarios:desativar"
    assert kwargs["event"].entity_type == "usuario"
    assert kwargs["event"].entity_id == "usr_target"
    assert kwargs["event"].request_id == "req_0123456789abcdef0123456789abcdef"
    assert kwargs["audit_sink"] is sink


def test_service_blocks_self_deactivation():
    repository = DeactivationRepository(user("ADMIN@example.com"))
    service = UsuariosService(
        repository=repository, audit_sink=TransactionalAuditSink()
    )

    with pytest.raises(HTTPException) as error:
        service.deactivate(
            "usr_target",
            actor=AuthenticatedPrincipal(subject="google-subject-admin", email=" admin@example.com ", profile="Admin", account_status="Ativo"),
        )

    assert error.value.status_code == 403
    assert repository.call is None


def test_service_fails_closed_when_audited_deactivation_is_unavailable():
    repository = DeactivationRepository(user())
    service = UsuariosService(repository=repository)

    with pytest.raises(HTTPException) as error:
        service.deactivate(
            "usr_target",
            actor=AuthenticatedPrincipal(subject="google-subject-admin", email="admin@example.com", profile="Admin", account_status="Ativo"),
        )

    assert error.value.status_code == 503
    assert repository.call is None


@pytest.mark.parametrize("actor", [None, object(), AuthenticatedPrincipal(subject="google-subject-admin", email="admin@example.com", profile="Admin", account_status="Inativo"), AuthenticatedPrincipal(subject=" ", email="admin@example.com", profile="Admin", account_status="Ativo")])
def test_deactivation_requires_valid_active_authenticated_principal(actor):
    repository = DeactivationRepository(user())
    service = UsuariosService(repository=repository, audit_sink=TransactionalAuditSink())
    with pytest.raises(HTTPException) as error:
        service.deactivate("usr_target", actor=actor)
    assert error.value.status_code == 401
    assert repository.call is None
