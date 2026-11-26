import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core.authentication import get_current_principal
from app.core.authorization import AuthenticatedPrincipal
from app.main import create_app
from app.modules.moradores.schemas import MoradorImportBatch, MoradorInput
from app.modules.moradores.service import MoradoresService


def build_client(profile: str | None = None) -> TestClient:
    application = create_app(storage_backend="memory")
    if profile is not None:
        async def authenticated_principal() -> AuthenticatedPrincipal:
            return AuthenticatedPrincipal(subject="google-test-subject", email="teste@example.com", profile=profile, account_status="Ativo")
        application.dependency_overrides[get_current_principal] = authenticated_principal
    return TestClient(application)


def test_all_resident_routes_require_authentication():
    client = build_client()
    requests = [
        ("GET", "/api/v1/moradores", None),
        ("POST", "/api/v1/moradores", {"bloco": "1", "apartamento": "101", "nome": "Ana"}),
        ("PUT", "/api/v1/moradores/id-teste", {"bloco": "1", "apartamento": "101", "nome": "Ana"}),
        ("DELETE", "/api/v1/moradores/id-teste", None),
        ("POST", "/api/v1/moradores/importar", {"moradores": []}),
    ]
    for method, path, payload in requests:
        assert client.request(method, path, json=payload).status_code == 401


def test_both_profiles_are_denied_resident_actions_until_matrix_approval():
    requests = [
        ("GET", "/api/v1/moradores", None),
        ("POST", "/api/v1/moradores", {"bloco": "1", "apartamento": "101", "nome": "Ana"}),
        ("PUT", "/api/v1/moradores/id-teste", {"bloco": "1", "apartamento": "101", "nome": "Ana"}),
        ("DELETE", "/api/v1/moradores/id-teste", None),
        ("POST", "/api/v1/moradores/importar", {"moradores": []}),
    ]
    for profile in ("Admin", "Operador"):
        client = build_client(profile)
        for method, path, payload in requests:
            assert client.request(method, path, json=payload).status_code == 403


def test_resident_service_crud_filters_and_import():
    service = MoradoresService()
    data = MoradorInput(bloco="1", apartamento="101", nome="Ana Maria", email="ana@example.com", telefone="41999990000", cpf="123", petNome="Mimi", vagaGaragem="G12")
    item = service.create(data)
    assert service.list(bloco="1", busca="ana") == [item]
    updated = service.update(item.id, MoradorInput(bloco="2", apartamento="202", nome="Ana Maria"))
    assert updated.bloco == "2"
    assert service.import_batch(MoradorImportBatch(moradores=[{"bloco":"3","apartamento":"301","nome":"Carlos"}])) == 1
    assert len(service.list()) == 2
    service.delete(item.id)
    with pytest.raises(HTTPException) as error:
        service.delete(item.id)
    assert error.value.status_code == 404


def test_resident_required_fields_and_text_normalization():
    with pytest.raises(Exception):
        MoradorInput(bloco="1", apartamento="   ", nome="Ana")
    item = MoradorInput(bloco=" 1 ", apartamento=" 101 ", nome=" Ana ", email=" ana@example.com ", telefone=" (41) 99999-0000 ")
    assert (item.bloco, item.apartamento, item.nome, item.email, item.telefone) == ("1", "101", "Ana", "ana@example.com", "(41) 99999-0000")
