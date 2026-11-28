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


def test_category_and_reason_routes_require_authentication():
    client = build_client()
    requests = [
        ("GET", "/api/v1/categorias", None),
        ("POST", "/api/v1/categorias", {"nome": "Financeiro"}),
        ("DELETE", "/api/v1/categorias/1", None),
        ("GET", "/api/v1/motivos-acerto-estoque", None),
        ("POST", "/api/v1/motivos-acerto-estoque", {"nome": "Quebra"}),
        ("DELETE", "/api/v1/motivos-acerto-estoque/1", None),
    ]
    for method, path, payload in requests:
        response = client.request(method, path, json=payload)
        assert response.status_code == 401, (method, path, response.text)


def test_category_and_reason_routes_deny_both_profiles_until_approval():
    requests = [
        ("GET", "/api/v1/categorias", None),
        ("POST", "/api/v1/categorias", {"nome": "Financeiro"}),
        ("DELETE", "/api/v1/categorias/1", None),
        ("GET", "/api/v1/motivos-acerto-estoque", None),
        ("POST", "/api/v1/motivos-acerto-estoque", {"nome": "Quebra"}),
        ("DELETE", "/api/v1/motivos-acerto-estoque/1", None),
    ]
    for profile in ("Admin", "Operador"):
        client = build_client(profile)
        for method, path, payload in requests:
            response = client.request(method, path, json=payload)
            assert response.status_code == 403, (profile, method, path, response.text)


import pytest
from fastapi import HTTPException

from app.core.authorization import AuthenticatedPrincipal
from app.core.repositories import InMemoryCollectionRepository
from app.modules.categorias.schemas import CategoriaInput
from app.modules.categorias.service import CategoriasService
from app.modules.motivos_acerto.schemas import MotivoAcertoInput
from app.modules.motivos_acerto.service import MotivosAcertoService


class AuditedCatalogRepository(InMemoryCollectionRepository):
    def __init__(self):
        super().__init__()
        self.events = []

    def add_audited(self, item_id, item, event, audit_sink):
        self.add(item_id, item)
        audit_sink.append_in_transaction(None, event)
        self.events.append(event)

    def delete_audited(self, item_id, event, audit_sink):
        audit_sink.append_in_transaction(None, event)
        self.delete(item_id)
        self.events.append(event)


class TestSink:
    def __init__(self):
        self.events = []

    def append_in_transaction(self, connection, event):
        self.events.append(event)


@pytest.mark.parametrize(
    ("service_type", "input_type", "name"),
    [
        (CategoriasService, CategoriaInput, "Financeiro"),
        (MotivosAcertoService, MotivoAcertoInput, "Quebra"),
    ],
)
def test_catalog_services_require_active_actor_and_audit_create_delete(service_type, input_type, name):
    repository = AuditedCatalogRepository()
    sink = TestSink()
    service = service_type(repository=repository, audit_sink=sink)
    actor = AuthenticatedPrincipal(
        subject="google-test-subject",
        email="teste@example.com",
        profile="Admin",
        account_status="Ativo",
    )

    with pytest.raises(HTTPException) as denied:
        service.create(input_type(nome=name))
    assert denied.value.status_code == 403
    assert repository.list() == []

    item = service.create(input_type(nome=name), actor=actor, request_id="req_create")
    assert repository.get(item.id) == item
    assert sink.events[-1].request_id == "req_create"
    assert sink.events[-1].actor_subject == actor.subject

    service.delete(item.id, actor=actor, request_id="req_delete")
    assert repository.get(item.id) is None
    assert sink.events[-1].request_id == "req_delete"
    assert len(sink.events) == 2
