from fastapi.testclient import TestClient
import pytest
from pydantic import ValidationError

from app.core.authentication import get_current_principal
from app.core.authorization import AuthenticatedPrincipal
from app.main import create_app
from app.modules.formas_monetarias.schemas import FormaMonetariaInput


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


def test_all_formas_monetarias_routes_require_authentication():
    client = build_client()
    assert client.get("/api/v1/formas-monetarias").status_code == 401
    assert client.post("/api/v1/formas-monetarias", json={"nome": "Boleto"}).status_code == 401
    assert client.put("/api/v1/formas-monetarias/1", json={"nome": "PIX"}).status_code == 401
    assert client.delete("/api/v1/formas-monetarias/1").status_code == 401



def test_admin_has_full_formas_monetarias_access():
    client = build_client("Admin")
    assert client.get("/api/v1/formas-monetarias").status_code == 200
    created = client.post("/api/v1/formas-monetarias", json={"nome": "Boleto"})
    assert created.status_code == 201
    item_id = created.json()["id"]
    assert client.put(f"/api/v1/formas-monetarias/{item_id}", json={"nome": "PIX"}).status_code == 200
    assert client.delete(f"/api/v1/formas-monetarias/{item_id}").status_code == 204

def test_operator_has_read_only_formas_monetarias_access():
    client = build_client("Operador")
    assert client.get("/api/v1/formas-monetarias").status_code == 200
    assert client.post("/api/v1/formas-monetarias", json={"nome": "Boleto"}).status_code == 403
    assert client.put("/api/v1/formas-monetarias/missing", json={"nome": "PIX"}).status_code == 403
    assert client.delete("/api/v1/formas-monetarias/missing").status_code == 403
@pytest.mark.parametrize("multa_pct", [0, 2, 2.01, 100])
def test_forma_monetaria_accepts_multa_within_range(multa_pct):
    data = FormaMonetariaInput(nome="PIX", multaPct=multa_pct)
    assert data.multaPct == multa_pct


@pytest.mark.parametrize("multa_pct", [-0.01, 100.01, 1.234, float("nan"), float("inf"), float("-inf")])
def test_forma_monetaria_rejects_multa_outside_range_or_non_finite(multa_pct):
    with pytest.raises(ValidationError):
        FormaMonetariaInput(nome="PIX", multaPct=multa_pct)


def test_postgres_style_audit_configuration_fails_closed_for_all_mutations():
    from fastapi import HTTPException
    from app.core.repositories import InMemoryCollectionRepository
    from app.modules.formas_monetarias.service import FormasMonetariasService

    service = FormasMonetariasService(
        repository=InMemoryCollectionRepository(),
        audit_sink=object(),
    )
    operations = [
        lambda: service.create(FormaMonetariaInput(nome="PIX")),
        lambda: service.update("missing", FormaMonetariaInput(nome="Boleto")),
        lambda: service.delete("missing"),
    ]
    for operation in operations:
        with pytest.raises(HTTPException) as error:
            operation()
        assert error.value.status_code == 403
    assert service.list() == []


def test_authenticated_mutations_use_audited_repository_contract():
    from app.core.repositories import InMemoryCollectionRepository
    from app.core.audit import AuditEvent
    from app.modules.formas_monetarias.service import FormasMonetariasService

    class Sink:
        def __init__(self):
            self.events = []
        def append_in_transaction(self, connection, event):
            assert connection is self
            self.events.append(event)

    class AuditedRepository(InMemoryCollectionRepository):
        def add_audited(self, item, event, sink):
            super().add(item.id, item)
            sink.append_in_transaction(sink, event)
        def replace_audited(self, item_id, item, event, sink):
            super().replace(item_id, item)
            sink.append_in_transaction(sink, event)
        def delete_audited(self, item_id, event, sink):
            super().delete(item_id)
            sink.append_in_transaction(sink, event)

    sink = Sink()
    service = FormasMonetariasService(repository=AuditedRepository(), audit_sink=sink)
    actor = AuthenticatedPrincipal("google-subject", "teste@example.com", "Admin", "Ativo")
    created = service.create(FormaMonetariaInput(nome="PIX"), actor=actor, request_id="req-1")
    updated = service.update(created.id, FormaMonetariaInput(nome="Boleto"), actor=actor, request_id="req-2")
    service.delete(updated.id, actor=actor, request_id="req-3")
    assert [event.action for event in sink.events] == [
        "formas_monetarias:create", "formas_monetarias:update", "formas_monetarias:delete"
    ]
    assert [event.request_id for event in sink.events] == ["req-1", "req-2", "req-3"]
    assert service.list() == []
