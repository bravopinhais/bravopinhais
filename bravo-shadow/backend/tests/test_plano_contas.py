from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.modules.plano_contas.schemas import PlanoContaInput
from app.modules.plano_contas.service import PlanoContasService, plano_contas_service

client = TestClient(app)


def setup_function() -> None:
    plano_contas_service._items.clear()


def payload(**overrides):
    data = {"codigo": "1.1", "nome": "Taxa Ordinária", "tipo": "Receita"}
    data.update(overrides)
    return data


def test_create_and_list_account():
    created = client.post("/api/v1/plano-contas", json=payload())
    assert created.status_code == 201
    assert created.json()["codigo"] == "1.1"
    assert len(client.get("/api/v1/plano-contas").json()) == 1


def test_reject_duplicate_code_case_insensitive():
    assert client.post("/api/v1/plano-contas", json=payload()).status_code == 201
    duplicate = client.post("/api/v1/plano-contas", json=payload(codigo="1.1"))
    assert duplicate.status_code == 409


def test_update_account():
    created = client.post("/api/v1/plano-contas", json=payload()).json()
    updated = client.put(
        f"/api/v1/plano-contas/{created['id']}",
        json=payload(nome="Taxa atualizada", tipo="Despesa"),
    )
    assert updated.status_code == 200
    assert updated.json()["nome"] == "Taxa atualizada"
    assert updated.json()["tipo"] == "Despesa"


def test_delete_fails_closed_without_financial_reference_checker():
    created = client.post("/api/v1/plano-contas", json=payload()).json()
    response = client.delete(f"/api/v1/plano-contas/{created['id']}")
    assert response.status_code == 503
    assert len(client.get("/api/v1/plano-contas").json()) == 1


def test_delete_rejected_when_financial_references_exist():
    service = PlanoContasService(has_financial_references=lambda _account_id: True)
    item = service.create(PlanoContaInput(**payload()))
    try:
        service.delete(item.id)
        assert False, "A exclusão deveria ter sido bloqueada."
    except HTTPException as exc:
        assert exc.status_code == 409
        assert service.list()


def test_delete_allowed_only_after_reference_check_returns_false():
    service = PlanoContasService(has_financial_references=lambda _account_id: False)
    item = service.create(PlanoContaInput(**payload()))
    service.delete(item.id)
    assert service.list() == []


def test_invalid_type_is_rejected():
    response = client.post("/api/v1/plano-contas", json=payload(tipo="Transferência"))
    assert response.status_code == 422
