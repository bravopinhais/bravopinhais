import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.authentication import get_current_principal
from app.core.authorization import AuthenticatedPrincipal
from app.main import create_app
from app.modules.fornecedores.schemas import FornecedorInput
from app.modules.fornecedores.service import FornecedoresService


def build_client(profile: str | None = None) -> TestClient:
    application = create_app(storage_backend="memory")
    if profile is not None:
        async def authenticated_principal() -> AuthenticatedPrincipal:
            return AuthenticatedPrincipal(subject="google-test-subject", email="teste@example.com", profile=profile, account_status="Ativo")
        application.dependency_overrides[get_current_principal] = authenticated_principal
    return TestClient(application)


def test_all_fornecedores_routes_require_authentication():
    client = build_client()
    requests = [
        ("GET", "/api/v1/fornecedores", None),
        ("POST", "/api/v1/fornecedores", {"cnpj": "12.345.678/0001-90", "razaoSocial": "Fornecedor Exemplo"}),
        ("PUT", "/api/v1/fornecedores/id-teste", {"cnpj": "12.345.678/0001-90", "razaoSocial": "Fornecedor Exemplo"}),
        ("DELETE", "/api/v1/fornecedores/id-teste", None),
    ]
    for method, path, payload in requests:
        assert client.request(method, path, json=payload).status_code == 401



def test_both_profiles_have_approved_supplier_crud_capabilities():
    payload = {"cnpj": "12.345.678/0001-90", "razaoSocial": "Fornecedor Exemplo"}
    for profile in ("Admin", "Operador"):
        client = build_client(profile)
        assert client.get("/api/v1/fornecedores").status_code == 200
        created = client.post("/api/v1/fornecedores", json=payload)
        assert created.status_code == 201
        item_id = created.json()["id"]
        assert client.put(f"/api/v1/fornecedores/{item_id}", json=payload).status_code == 200
        assert client.delete(f"/api/v1/fornecedores/{item_id}").status_code == 204
def test_fornecedores_service_keeps_crud_and_validation_independent_from_http_auth():
    service = FornecedoresService()
    data = FornecedorInput.model_validate({"cnpj": "12.345.678/0001-90", "razaoSocial": "Fornecedor Exemplo"})
    created = service.create(data)
    assert service.list() == [created]
    updated = service.update(created.id, data)
    assert updated.id == created.id
    service.delete(created.id)
    assert service.list() == []
    with pytest.raises(ValidationError):
        FornecedorInput.model_validate({})
