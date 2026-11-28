import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.authentication import get_current_principal
from app.core.authorization import AuthenticatedPrincipal
from app.main import create_app
from app.modules.empregados.schemas import EmpregadoInput
from app.modules.empregados.service import EmpregadosService


def build_client(profile: str | None = None) -> TestClient:
    application = create_app(storage_backend="memory")
    if profile is not None:
        async def authenticated_principal() -> AuthenticatedPrincipal:
            return AuthenticatedPrincipal(subject="google-test-subject", email="teste@example.com", profile=profile, account_status="Ativo")
        application.dependency_overrides[get_current_principal] = authenticated_principal
    return TestClient(application)


def test_all_empregados_routes_require_authentication():
    client = build_client()
    requests = [
        ("GET", "/api/v1/empregados", None),
        ("POST", "/api/v1/empregados", {"nome": "Maria Exemplo", "cargo": "Zeladora", "telefone": "41999990000", "contatoEmergenciaNome": "João", "contatoEmergenciaTel": "41988887777"}),
        ("PUT", "/api/v1/empregados/id-teste", {"nome": "Maria Exemplo", "cargo": "Zeladora", "telefone": "41999990000", "contatoEmergenciaNome": "João", "contatoEmergenciaTel": "41988887777"}),
        ("DELETE", "/api/v1/empregados/id-teste", None),
    ]
    for method, path, payload in requests:
        assert client.request(method, path, json=payload).status_code == 401



def test_both_profiles_have_approved_employee_crud_capabilities():
    payload = {"nome": "Maria Exemplo", "cargo": "Zeladora", "telefone": "41999990000", "contatoEmergenciaNome": "João", "contatoEmergenciaTel": "41988887777"}
    for profile in ("Admin", "Operador"):
        client = build_client(profile)
        assert client.get("/api/v1/empregados").status_code == 200
        created = client.post("/api/v1/empregados", json=payload)
        assert created.status_code == 201
        item_id = created.json()["id"]
        assert client.put(f"/api/v1/empregados/{item_id}", json=payload).status_code == 200
        assert client.delete(f"/api/v1/empregados/{item_id}").status_code == 204
def test_empregados_service_keeps_crud_and_validation_independent_from_http_auth():
    service = EmpregadosService()
    data = EmpregadoInput.model_validate({"nome": "Maria Exemplo", "cargo": "Zeladora", "telefone": "41999990000", "contatoEmergenciaNome": "João", "contatoEmergenciaTel": "41988887777"})
    created = service.create(data)
    assert service.list() == [created]
    updated = service.update(created.id, data)
    assert updated.id == created.id
    service.delete(created.id)
    assert service.list() == []
    with pytest.raises(ValidationError):
        EmpregadoInput.model_validate({})
