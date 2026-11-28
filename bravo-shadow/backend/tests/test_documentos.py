import pytest
from types import MappingProxyType
from app.core.authentication import get_current_principal
from app.core.authorization import AuthenticatedPrincipal, CAPABILITIES
from app.core import authorization
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.modules.categorias.schemas import CategoriaInput

from app.main import app, create_app


@pytest.fixture(autouse=True)
def allow_test_admin(monkeypatch):
    monkeypatch.setattr(
        authorization,
        "ROLE_CAPABILITIES",
        MappingProxyType({"Admin": CAPABILITIES, "Operador": frozenset()}),
    )
    async def authenticated_admin():
        return AuthenticatedPrincipal(
            subject="google-test-subject", email="teste@example.com",
            profile="Admin", account_status="Ativo",
        )
    app.dependency_overrides[get_current_principal] = authenticated_admin
    yield
    app.dependency_overrides.clear()


client = TestClient(app)


def setup_function():
    app.state.services.documentos._items.clear()
    app.state.services.categorias._items.clear()


def payload(**overrides):
    data = {
        "pasta": "Financeiro",
        "titulo": "Ata de reunião",
        "nomeArquivo": "ata.pdf",
        "arquivoCompactadoGzip": "H4sIAAAAAAAC/1MNcHHTNdQz4TJUMFDIT8risrFR0A+pLEhV0HdOLEnMyU9XsLPjSs1LAcmpqrr6u3EBAARwAM8zAAAA",
    }
    data.update(overrides)
    return data


def test_document_crud_preserves_file_payload_and_original_name():
    created = client.post("/api/v1/documentos", json=payload())
    assert created.status_code == 201
    item = created.json()
    assert item["nomeArquivo"] == "ata.pdf"
    detail = client.get("/api/v1/documentos/" + item["id"])
    assert detail.status_code == 200
    assert detail.json()["arquivoCompactadoGzip"] == "H4sIAAAAAAAC/1MNcHHTNdQz4TJUMFDIT8risrFR0A+pLEhV0HdOLEnMyU9XsLPjSs1LAcmpqrr6u3EBAARwAM8zAAAA"
    assert client.get("/api/v1/documentos/" + item["id"]).status_code == 200
    changed = client.put(
        "/api/v1/documentos/" + item["id"],
        json=payload(titulo="Ata atualizada"),
    )
    assert changed.status_code == 200 and changed.json()["titulo"] == "Ata atualizada"
    assert client.delete("/api/v1/documentos/" + item["id"]).status_code == 204


def test_document_not_found():
    assert client.get("/api/v1/documentos/inexistente").status_code == 404
    assert client.delete("/api/v1/documentos/inexistente").status_code == 404


def test_document_requires_file_content():
    data = payload()
    data["arquivoCompactadoGzip"] = ""
    assert client.post("/api/v1/documentos", json=data).status_code == 422


def test_documents_are_isolated_between_app_instances():
    first_app, second_app = create_app(), create_app()

    async def authenticated_admin():
        return AuthenticatedPrincipal(
            subject="google-test-subject", email="teste@example.com",
            profile="Admin", account_status="Ativo",
        )

    first_app.dependency_overrides[get_current_principal] = authenticated_admin
    second_app.dependency_overrides[get_current_principal] = authenticated_admin
    first = TestClient(first_app)
    second = TestClient(second_app)

    created = first.post("/api/v1/documentos", json=payload()).json()
    assert first.get("/api/v1/documentos/" + created["id"]).status_code == 200
    assert second.get("/api/v1/documentos").json() == []
    assert second.get("/api/v1/documentos/" + created["id"]).status_code == 404


def test_document_category_link_and_restrict_delete():
    category = app.state.services.categorias.create(CategoriaInput(nome="Atas"))
    created = client.post(
        "/api/v1/documentos",
        json=payload(categoriaId=category.id, pasta="Nome antigo"),
    )
    assert created.status_code == 201
    document = created.json()
    assert document["categoriaId"] == category.id
    assert document["pasta"] == "Atas"
    with pytest.raises(HTTPException) as error:
        app.state.services.categorias.delete(category.id)
    assert error.value.status_code == 409
    assert client.delete("/api/v1/documentos/" + document["id"]).status_code == 204
    app.state.services.categorias.delete(category.id)
def test_document_rejects_unknown_category():
    response = client.post(
        "/api/v1/documentos",
        json=payload(categoriaId="categoria-inexistente"),
    )
    assert response.status_code == 404


def test_document_metadata_is_trimmed_and_compressed_content_is_preserved():
    compressed_payload = "H4sIAAAAAAAC/1MNcHHTNdQz4TJUMFDIT8risrFR0A+pLEhV0HdOLEnMyU9XsLPjSs1LAcmpqrr6u3EBAARwAM8zAAAA"
    response = client.post(
        "/api/v1/documentos",
        json=payload(
            pasta="  Financeiro  ",
            categoriaId="  ",
            titulo="  Ata de reunião  ",
            nomeArquivo="  ata final.pdf  ",
            arquivoCompactadoGzip=compressed_payload,
        ),
    )
    assert response.status_code == 201
    item = response.json()
    assert item["pasta"] == "Financeiro"
    assert item["categoriaId"] is None
    assert item["titulo"] == "Ata de reunião"
    assert item["nomeArquivo"] == "ata final.pdf"
    detail = client.get("/api/v1/documentos/" + item["id"])
    assert detail.status_code == 200
    assert detail.json()["arquivoCompactadoGzip"] == compressed_payload


def test_document_required_metadata_rejects_whitespace_only():
    assert client.post("/api/v1/documentos", json=payload(titulo="   ")).status_code == 422
    assert client.post("/api/v1/documentos", json=payload(nomeArquivo="   ")).status_code == 422


def test_document_category_id_is_trimmed_before_lookup():
    category = app.state.services.categorias.create(CategoriaInput(nome="Atas"))
    response = client.post(
        "/api/v1/documentos",
        json=payload(categoriaId=f"  {category.id}  "),
    )
    assert response.status_code == 201
    assert response.json()["categoriaId"] == category.id
    assert response.json()["pasta"] == "Atas"



def test_document_routes_require_authentication():
    unauthenticated = TestClient(create_app(storage_backend="memory"))
    assert unauthenticated.get("/api/v1/documentos").status_code == 401
    assert unauthenticated.get("/api/v1/documentos/x").status_code == 401
    assert unauthenticated.post("/api/v1/documentos", json=payload()).status_code == 401
    assert unauthenticated.put("/api/v1/documentos/x", json=payload()).status_code == 401
    assert unauthenticated.delete("/api/v1/documentos/x").status_code == 401


def test_document_routes_deny_profiles_until_matrix_approval(monkeypatch):
    monkeypatch.setattr(
        authorization,
        "ROLE_CAPABILITIES",
        MappingProxyType({"Admin": frozenset(), "Operador": frozenset()}),
    )
    for profile in ("Admin", "Operador"):
        application = create_app(storage_backend="memory")
        async def principal(profile=profile):
            return AuthenticatedPrincipal(
                subject="google-test-subject", email="teste@example.com",
                profile=profile, account_status="Ativo",
            )
        application.dependency_overrides[get_current_principal] = principal
        denied = TestClient(application)
        assert denied.get("/api/v1/documentos").status_code == 403
        assert denied.get("/api/v1/documentos/x").status_code == 403
        assert denied.post("/api/v1/documentos", json=payload()).status_code == 403
        assert denied.put("/api/v1/documentos/x", json=payload()).status_code == 403
        assert denied.delete("/api/v1/documentos/x").status_code == 403


from app.core.authorization import AuthenticatedPrincipal
from app.core.repositories import InMemoryCollectionRepository
from app.modules.documentos.schemas import DocumentoInput
from app.modules.documentos.service import DocumentosService


class AuditedDocumentRepository(InMemoryCollectionRepository):
    def add_audited(self, item_id, item, event, audit_sink):
        audit_sink.append_in_transaction(None, event)
        self.add(item_id, item)

    def replace_audited(self, item_id, item, event, audit_sink):
        audit_sink.append_in_transaction(None, event)
        self.replace(item_id, item)

    def delete_audited(self, item_id, event, audit_sink):
        audit_sink.append_in_transaction(None, event)
        self.delete(item_id)


class DocumentAuditSink:
    def __init__(self):
        self.events = []

    def append_in_transaction(self, connection, event):
        self.events.append(event)


def test_document_service_requires_actor_and_uses_audited_contract():
    repository = AuditedDocumentRepository()
    sink = DocumentAuditSink()
    service = DocumentosService(repository=repository, audit_sink=sink)
    actor = AuthenticatedPrincipal(
        subject="google-test-subject",
        email="teste@example.com",
        profile="Admin",
        account_status="Ativo",
    )
    data = DocumentoInput.model_construct(
        pasta="Financeiro", categoriaId=None, titulo="Ata",
        nomeArquivo="ata.pdf", arquivoCompactadoGzip="gzip-data",
    )

    with pytest.raises(HTTPException) as denied:
        service.create(data)
    assert denied.value.status_code == 403
    assert repository.list() == []

    item = service.create(data, actor=actor, request_id="req_doc_create")
    assert repository.get(item.id) == item
    assert sink.events[-1].action == "documentos:create"
    assert sink.events[-1].request_id == "req_doc_create"

    updated = service.update(
        item.id, data.model_copy(update={"titulo": "Ata atualizada"}),
        actor=actor, request_id="req_doc_update",
    )
    assert updated.titulo == "Ata atualizada"
    assert sink.events[-1].action == "documentos:update"

    service.delete(item.id, actor=actor, request_id="req_doc_delete")
    assert repository.get(item.id) is None
    assert sink.events[-1].action == "documentos:delete"
    assert [event.request_id for event in sink.events] == [
        "req_doc_create", "req_doc_update", "req_doc_delete",
    ]


class ReadAuditSink:
    def __init__(self, *, fail=False):
        self.events = []
        self.fail = fail

    def append(self, event):
        if self.fail:
            raise RuntimeError("private audit backend detail")
        self.events.append(event)


def test_document_list_and_detail_reads_are_audited_without_document_content():
    sink = ReadAuditSink()
    app.state.services.documentos.audit_sink = sink
    created = client.post("/api/v1/documentos", json=payload())
    assert created.status_code == 201
    sink.events.clear()

    listed = client.get("/api/v1/documentos")
    detail = client.get("/api/v1/documentos/" + created.json()["id"])

    assert listed.status_code == 200
    assert detail.status_code == 200
    assert [(event.action, event.entity_type, event.entity_id) for event in sink.events] == [
        ("documentos:list", "documento", None),
        ("documentos:read", "documento", created.json()["id"]),
    ]
    assert all(event.actor_subject == "google-test-subject" for event in sink.events)
    assert all(event.request_id for event in sink.events)
    assert all(not hasattr(event, "email") for event in sink.events)
    assert all(not hasattr(event, "payload") for event in sink.events)


def test_document_reads_fail_closed_when_audit_storage_is_unavailable():
    app.state.services.documentos.audit_sink = ReadAuditSink(fail=True)

    listed = client.get("/api/v1/documentos")
    detail = client.get("/api/v1/documentos/inexistente")

    assert listed.status_code == 503
    assert detail.status_code == 503
    assert "private audit backend detail" not in listed.text
    assert "private audit backend detail" not in detail.text
