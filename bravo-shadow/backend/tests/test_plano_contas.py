import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.authentication import get_current_principal
from app.core.authorization import AuthenticatedPrincipal
from app.main import create_app
from app.modules.plano_contas.schemas import PlanoContaInput
from app.modules.plano_contas.service import PlanoContasService


def build_client(profile: str | None = None) -> TestClient:
    application = create_app(storage_backend="memory")
    if profile is not None:
        async def authenticated_principal() -> AuthenticatedPrincipal:
            return AuthenticatedPrincipal(subject="google-test-subject", email="teste@example.com", profile=profile, account_status="Ativo")
        application.dependency_overrides[get_current_principal] = authenticated_principal
    return TestClient(application)


def payload(**overrides):
    data = {"codigo": "1.1", "nome": "Taxa Ordinária", "tipo": "Receita"}
    data.update(overrides)
    return data


def build_service(checker=lambda _account_id: False):
    return PlanoContasService(has_financial_references=checker)


def test_all_account_routes_require_authentication():
    client = build_client()
    requests = [
        ("GET", "/api/v1/plano-contas", None),
        ("POST", "/api/v1/plano-contas", payload()),
        ("PUT", "/api/v1/plano-contas/id-teste", payload()),
        ("DELETE", "/api/v1/plano-contas/id-teste", None),
    ]
    for method, path, body in requests:
        assert client.request(method, path, json=body).status_code == 401



def test_plan_accounts_are_readable_by_both_and_mutable_by_admin_only():
    admin = build_client("Admin")
    operator = build_client("Operador")
    assert admin.get("/api/v1/plano-contas").status_code == 200
    assert operator.get("/api/v1/plano-contas").status_code == 200
    created = admin.post("/api/v1/plano-contas", json=payload())
    assert created.status_code == 201
    item_id = created.json()["id"]
    assert admin.put(f"/api/v1/plano-contas/{item_id}", json=payload(nome="Taxa atualizada")).status_code == 200
    assert admin.delete(f"/api/v1/plano-contas/{item_id}").status_code == 204
    assert operator.post("/api/v1/plano-contas", json=payload(codigo="2.1")).status_code == 403
    assert operator.put(f"/api/v1/plano-contas/{item_id}", json=payload()).status_code == 403
    assert operator.delete(f"/api/v1/plano-contas/{item_id}").status_code == 403
def test_create_list_and_reject_duplicate_code_case_insensitive():
    service = build_service()
    created = service.create(PlanoContaInput(**payload(codigo="ABC-1")))
    assert created.codigo == "ABC-1"
    assert service.list() == [created]
    with pytest.raises(HTTPException) as error:
        service.create(PlanoContaInput(**payload(codigo="abc-1")))
    assert error.value.status_code == 409


def test_account_code_and_name_are_trimmed_and_required():
    created = build_service().create(PlanoContaInput(**payload(codigo="  2.1  ", nome="  Fundo de Reserva  ")))
    assert created.codigo == "2.1"
    assert created.nome == "Fundo de Reserva"
    with pytest.raises(ValidationError):
        PlanoContaInput(**payload(codigo="   "))
    with pytest.raises(ValidationError):
        PlanoContaInput(**payload(nome="   "))


def test_update_uses_optimistic_version_and_rejects_stale_version():
    service = build_service()
    created = service.create(PlanoContaInput(**payload()))
    updated = service.update(created.id, PlanoContaInput(**payload(nome="Taxa atualizada", tipo="Despesa")), created.version)
    assert updated.version == 2
    assert updated.nome == "Taxa atualizada"
    with pytest.raises(HTTPException) as error:
        service.update(created.id, PlanoContaInput(**payload(nome="Alteração antiga")), created.version)
    assert error.value.status_code == 409
    assert service.list()[0].nome == "Taxa atualizada"


def test_delete_fails_closed_without_financial_reference_checker():
    service = PlanoContasService()
    created = service.create(PlanoContaInput(**payload()))
    with pytest.raises(HTTPException) as error:
        service.delete(created.id)
    assert error.value.status_code == 503
    assert len(service.list()) == 1


def test_delete_rejected_when_financial_references_exist():
    service = build_service(lambda _account_id: True)
    created = service.create(PlanoContaInput(**payload()))
    with pytest.raises(HTTPException) as error:
        service.delete(created.id)
    assert error.value.status_code == 409
    assert service.list()


def test_delete_allowed_only_after_reference_check_returns_false():
    service = build_service()
    created = service.create(PlanoContaInput(**payload()))
    service.delete(created.id)
    assert service.list() == []



def test_audited_storage_rejects_mutations_without_authenticated_actor():
    service = build_service()
    created = service.create(PlanoContaInput(**payload()))
    service.audit_sink = object()

    operations = [
        lambda: service.create(PlanoContaInput(**payload(codigo="2.1"))),
        lambda: service.update(
            created.id,
            PlanoContaInput(**payload(nome="Alteração sem ator")),
            created.version,
        ),
        lambda: service.delete(created.id),
    ]
    for operation in operations:
        with pytest.raises(HTTPException) as error:
            operation()
        assert error.value.status_code == 403

    assert service.list() == [created]


def test_invalid_type_is_rejected():
    with pytest.raises(ValidationError):
        PlanoContaInput(**payload(tipo="Transferência"))
