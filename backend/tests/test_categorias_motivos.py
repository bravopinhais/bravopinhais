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



def test_category_and_reason_routes_follow_approved_capability_matrix():
    admin = build_client("Admin")
    operator = build_client("Operador")

    for client in (admin, operator):
        assert client.get("/api/v1/categorias").status_code == 200
        assert client.get("/api/v1/motivos-acerto-estoque").status_code == 200

    category = admin.post("/api/v1/categorias", json={"nome": "Financeiro"})
    assert category.status_code == 201
    assert operator.post("/api/v1/categorias", json={"nome": "Outra"}).status_code == 403
    assert admin.delete(f"/api/v1/categorias/{category.json()['id']}").status_code == 204
    assert operator.delete("/api/v1/categorias/missing").status_code == 403

    reason = admin.post("/api/v1/motivos-acerto-estoque", json={"nome": "Quebra"})
    assert reason.status_code == 201
    assert operator.post("/api/v1/motivos-acerto-estoque", json={"nome": "Outro"}).status_code == 403
    assert admin.delete(f"/api/v1/motivos-acerto-estoque/{reason.json()['id']}").status_code == 204
    assert operator.delete("/api/v1/motivos-acerto-estoque/missing").status_code == 403
def test_catalog_services_require_active_actor_and_audit_create_delete(service_type, input_type, name):
    repository = AuditedCatalogRepository()
    sink = FakeAuditSink()
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
