import pytest
from fastapi import HTTPException

from app.modules.usuarios.schemas import Usuario, UsuarioAdministracaoInput
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
        actor_subject="google-subject-admin",
        actor_email="admin@example.com",
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
            actor_subject="google-subject-admin",
            actor_email=" admin@example.com ",
            audit_sink=object(),
        )

    assert error.value.status_code == 403
    assert repository.call is None


def test_memory_repository_fails_closed_for_admin_changes():
    service = UsuariosService()
    created = service.create(
        __import__("app.modules.usuarios.schemas", fromlist=["UsuarioInput"]).UsuarioInput(
            email="target@example.com", nome="Pessoa", cargo="Conselho",
            perfil="Admin",
        )
    )

    with pytest.raises(HTTPException) as error:
        service.update_administrative_state(
            created.id,
            UsuarioAdministracaoInput(perfil="Operador", status="Inativo"),
            actor_subject="google-subject-admin",
            actor_email="admin@example.com",
            audit_sink=object(),
        )

    assert error.value.status_code == 503
    assert service.get(created.id).perfil == "Admin"
    assert service.get(created.id).status == "Ativo"
