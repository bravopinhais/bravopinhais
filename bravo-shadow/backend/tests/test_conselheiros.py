from fastapi.testclient import TestClient

from app.core.authentication import get_current_principal
from app.core.authorization import AuthenticatedPrincipal
from app.main import create_app


def build_client(profile: str | None = None) -> TestClient:
    application = create_app(storage_backend="memory")
    if profile is not None:
        async def authenticated_principal() -> AuthenticatedPrincipal:
            return AuthenticatedPrincipal(
                subject="google-test-subject",
                email="teste@example.com",
                profile=profile,
                account_status="Ativo",
            )
        application.dependency_overrides[get_current_principal] = authenticated_principal
    return TestClient(application)


def test_all_council_routes_require_authentication():
    client = build_client()
    assert client.get("/api/v1/conselheiros").status_code == 401
    assert client.post("/api/v1/conselheiros", json={"nome": "Pessoa", "cargo": "Síndico"}).status_code == 401
    assert client.put("/api/v1/conselheiros/1", json={"nome": "Pessoa", "cargo": "Síndico"}).status_code == 401
    assert client.delete("/api/v1/conselheiros/1").status_code == 401



def test_council_read_is_available_to_both_and_mutations_are_admin_only():
    admin = build_client("Admin")
    operator = build_client("Operador")
    assert admin.get("/api/v1/conselheiros").status_code == 200
    assert operator.get("/api/v1/conselheiros").status_code == 200
    payload = {"nome": "Pessoa", "cargo": "Síndico"}
    created = admin.post("/api/v1/conselheiros", json=payload)
    assert created.status_code == 201
    item_id = created.json()["id"]
    assert operator.post("/api/v1/conselheiros", json=payload).status_code == 403
    assert admin.put(f"/api/v1/conselheiros/{item_id}", json=payload).status_code == 200
    assert operator.put(f"/api/v1/conselheiros/{item_id}", json=payload).status_code == 403
    assert admin.delete(f"/api/v1/conselheiros/{item_id}").status_code == 204
    assert operator.delete(f"/api/v1/conselheiros/{item_id}").status_code == 403
import pytest
from fastapi import HTTPException
from app.core.repositories import InMemoryCollectionRepository
from app.modules.conselheiros.schemas import ConselheiroInput
from app.modules.conselheiros.service import ConselheirosService


class CouncilAuditSink:
    def __init__(self):
        self.events = []

    def append_in_transaction(self, connection, event):
        self.events.append(event)


class AuditedCouncilRepository(InMemoryCollectionRepository):
    def add_audited(self, item_id, item, event, sink):
        sink.append_in_transaction(None, event)
        self.add(item_id, item)

    def replace_audited(self, item_id, item, event, sink):
        sink.append_in_transaction(None, event)
        self.replace(item_id, item)

    def delete_audited(self, item_id, event, sink):
        sink.append_in_transaction(None, event)
        self.delete(item_id)


def test_council_service_requires_actor_and_audits_crud():
    repository = AuditedCouncilRepository()
    sink = CouncilAuditSink()
    service = ConselheirosService(repository=repository, audit_sink=sink)
    actor = AuthenticatedPrincipal(
        subject="google-test-subject", email="teste@example.com",
        profile="Admin", account_status="Ativo",
    )
    data = ConselheiroInput(nome="Ana", cargo="Síndica", BlocoAp="A-101", telefone="41999990000")

    with pytest.raises(HTTPException) as denied:
        service.create(data)
    assert denied.value.status_code == 403
    assert repository.list() == []

    item = service.create(data, actor=actor, request_id="req_create")
    changed = service.update(
        item.id, data.model_copy(update={"cargo": "Conselheira"}),
        actor=actor, request_id="req_update",
    )
    assert changed.cargo == "Conselheira"
    service.delete(item.id, actor=actor, request_id="req_delete")

    assert repository.get(item.id) is None
    assert [event.action for event in sink.events] == [
        "conselheiros:create", "conselheiros:update", "conselheiros:delete",
    ]
    assert [event.request_id for event in sink.events] == [
        "req_create", "req_update", "req_delete",
    ]
