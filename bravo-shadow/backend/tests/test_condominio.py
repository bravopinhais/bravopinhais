import pytest
from fastapi.testclient import TestClient

from app.core.authentication import get_current_principal
from app.core.authorization import AuthenticatedPrincipal
from app.main import create_app
from app.modules.condominio.schemas import CondominioPatch
from app.modules.condominio.service import CondominioService


def build_client(profile: str | None = None) -> TestClient:
    application = create_app(storage_backend="memory")
    if profile is not None:
        async def authenticated_principal() -> AuthenticatedPrincipal:
            return AuthenticatedPrincipal(subject="google-test-subject", email="teste@example.com", profile=profile, account_status="Ativo")
        application.dependency_overrides[get_current_principal] = authenticated_principal
    return TestClient(application)


def test_condominium_routes_require_authentication():
    client = build_client()
    assert client.get("/api/v1/condominio").status_code == 401
    assert client.put("/api/v1/condominio", json={"nome":"Residencial"}).status_code == 401


def test_admin_and_operator_are_denied_until_capability_matrix_approval():
    for profile in ("Admin", "Operador"):
        client = build_client(profile)
        assert client.get("/api/v1/condominio").status_code == 403
        assert client.put("/api/v1/condominio", json={"nome":"Residencial"}).status_code == 403


def test_condominium_patch_preserves_unedited_fields_and_trims_values():
    service = CondominioService()
    service.update(CondominioPatch(razaoSocial=" Condomínio Exemplo ", cidade=" Curitiba "))
    response = service.update(CondominioPatch(nome=" Residencial Exemplo ", telefone="4133330000"))
    assert response.razaoSocial == "Condomínio Exemplo"
    assert response.cidade == "Curitiba"
    assert response.nome == "Residencial Exemplo"
    assert response.telefone == "4133330000"


def test_condominium_schema_rejects_unknown_fields():
    with pytest.raises(Exception):
        CondominioPatch(campoInventado="x")


def test_condominium_is_isolated_between_service_instances():
    first, second = CondominioService(), CondominioService()
    first.update(CondominioPatch(nome="Condomínio A"))
    assert first.get().nome == "Condomínio A"
    assert second.get().nome is None


def test_condominium_patch_accepts_empty_optional_values():
    service = CondominioService()
    result = service.update(CondominioPatch(telefone="   ", email="  "))
    assert result.telefone == ""
    assert result.email == ""


from app.core.repositories import InMemoryCollectionRepository


class CondominioAuditSink:
    def __init__(self):
        self.events = []

    def append_in_transaction(self, connection, event):
        self.events.append(event)


class AuditedCondominioRepository(InMemoryCollectionRepository):
    def replace_audited(self, item_id, item, event, sink):
        current = self.get(item_id) or {}
        current.update(item)
        if self.exists(item_id):
            self.replace(item_id, current)
        else:
            self.add(item_id, current)
        sink.append_in_transaction(None, event)


def test_condominio_service_requires_actor_and_records_audit():
    repository = AuditedCondominioRepository()
    sink = CondominioAuditSink()
    service = CondominioService(repository=repository, audit_sink=sink)
    actor = AuthenticatedPrincipal(
        subject="google-test-subject", email="teste@example.com",
        profile="Admin", account_status="Ativo",
    )

    with pytest.raises(Exception):
        service.update(CondominioPatch(nome="Residencial"), request_id="req_missing_actor")
    assert repository.get("singleton") is None

    updated = service.update(
        CondominioPatch(nome=" Residencial "),
        actor=actor,
        request_id="req_condominio",
    )
    assert updated.nome == "Residencial"
    assert len(sink.events) == 1
    assert sink.events[0].action == "condominio:update"
    assert sink.events[0].request_id == "req_condominio"
