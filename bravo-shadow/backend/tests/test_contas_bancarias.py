from decimal import Decimal

import pytest
from types import MappingProxyType

from app.core.authentication import get_current_principal
from app.core.authorization import AuthenticatedPrincipal, CAPABILITIES
from app.core import authorization

def configure_test_auth(application):
    async def authenticated_admin():
        return AuthenticatedPrincipal(
            subject="google-test-subject",
            email="teste@example.com",
            profile="Admin",
            account_status="Ativo",
        )
    application.dependency_overrides[get_current_principal] = authenticated_admin

@pytest.fixture(autouse=True)
def allow_test_admin(monkeypatch):
    monkeypatch.setattr(
        authorization,
        "ROLE_CAPABILITIES",
        MappingProxyType({"Admin": CAPABILITIES, "Operador": frozenset()}),
    )
    configure_test_auth(app)
    yield
    app.dependency_overrides.clear()


from pydantic import ValidationError
from fastapi.testclient import TestClient

from app.modules.contas_bancarias.schemas import ContaBancariaInput

from app.main import app, create_app

client = TestClient(app)


def setup_function() -> None:
    app.state.services.contas_bancarias._items.clear()


def test_create_list_update_delete_bank_account():
    created = client.post("/api/v1/contas-bancarias", json={"banco": "Banco do Brasil", "saldo": 1250.5})
    assert created.status_code == 201
    item = created.json()
    assert item["saldo"] == 1250.5
    updated = client.put(f"/api/v1/contas-bancarias/{item['id']}", json={"banco": "Caixa", "saldo": 800})
    assert updated.status_code == 200
    assert updated.json()["banco"] == "Caixa"
    assert client.delete(f"/api/v1/contas-bancarias/{item['id']}").status_code == 204
    assert client.get("/api/v1/contas-bancarias").json() == []


def test_default_balance_and_missing_delete():
    created = client.post("/api/v1/contas-bancarias", json={"banco": "Cooperativa"})
    assert created.status_code == 201
    assert created.json()["saldo"] == 0.0
    assert client.delete("/api/v1/contas-bancarias/missing").status_code == 404


def test_bank_name_is_required():
    assert client.post("/api/v1/contas-bancarias", json={"banco": ""}).status_code == 422


def test_bank_accounts_are_isolated_between_app_instances():
    first_app, second_app = create_app(), create_app()
    configure_test_auth(first_app)
    configure_test_auth(second_app)
    first, second = TestClient(first_app), TestClient(second_app)
    created = first.post("/api/v1/contas-bancarias", json={"banco": "Conta Isolada"}).json()
    assert first.get("/api/v1/contas-bancarias").json()[0]["id"] == created["id"]
    assert second.get("/api/v1/contas-bancarias").json() == []



def test_bank_balance_uses_decimal_precision_and_rejects_more_than_two_places():
    item = ContaBancariaInput(banco="Banco", saldo="1234.56")
    assert item.saldo == Decimal("1234.56")
    with pytest.raises(ValidationError):
        ContaBancariaInput(banco="Banco", saldo="1234.567")


@pytest.mark.parametrize("saldo", ["NaN", "Infinity", "-Infinity"])
def test_bank_balance_rejects_non_finite_values(saldo):
    with pytest.raises(ValidationError):
        ContaBancariaInput(banco="Banco", saldo=saldo)


def test_bank_balance_allows_negative_values_for_legacy_compatibility():
    item = ContaBancariaInput(banco="Banco", saldo="-125.50")
    assert item.saldo == Decimal("-125.50")


def test_bank_name_is_trimmed_on_create():
    response = client.post(
        "/api/v1/contas-bancarias",
        json={"banco": "  Banco Cooperativo  ", "saldo": "10.00"},
    )
    assert response.status_code == 201
    assert response.json()["banco"] == "Banco Cooperativo"


def test_bank_name_with_only_whitespace_is_rejected():
    response = client.post(
        "/api/v1/contas-bancarias",
        json={"banco": "   ", "saldo": "10.00"},
    )
    assert response.status_code == 422


def test_bank_name_is_trimmed_on_update():
    created = client.post(
        "/api/v1/contas-bancarias", json={"banco": "Banco A", "saldo": 0}
    ).json()
    response = client.put(
        f"/api/v1/contas-bancarias/{created['id']}",
        json={"banco": "  Banco B  ", "saldo": 0},
    )
    assert response.status_code == 200
    assert response.json()["banco"] == "Banco B"


def test_postgres_style_audit_configuration_fails_closed_for_all_mutations():
    from fastapi import HTTPException
    from app.core.repositories import InMemoryCollectionRepository
    from app.modules.contas_bancarias.service import ContasBancariasService

    service = ContasBancariasService(
        repository=InMemoryCollectionRepository(),
        audit_sink=object(),
    )
    operations = [
        lambda: service.create(ContaBancariaInput(banco="Banco")),
        lambda: service.update("missing", ContaBancariaInput(banco="Banco")),
        lambda: service.delete("missing"),
    ]
    for operation in operations:
        with pytest.raises(HTTPException) as error:
            operation()
        assert error.value.status_code == 403
    assert service.list() == []


def test_authenticated_mutations_use_audited_repository_contract():
    from app.core.repositories import InMemoryCollectionRepository
    from app.modules.contas_bancarias.service import ContasBancariasService

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
    service = ContasBancariasService(repository=AuditedRepository(), audit_sink=sink)
    actor = AuthenticatedPrincipal("google-subject", "teste@example.com", "Admin", "Ativo")
    created = service.create(ContaBancariaInput(banco="Banco A"), actor=actor, request_id="req-1")
    updated = service.update(created.id, ContaBancariaInput(banco="Banco B"), actor=actor, request_id="req-2")
    service.delete(updated.id, actor=actor, request_id="req-3")
    assert [event.action for event in sink.events] == [
        "contas_bancarias:create", "contas_bancarias:update", "contas_bancarias:delete"
    ]
    assert [event.request_id for event in sink.events] == ["req-1", "req-2", "req-3"]
    assert service.list() == []
