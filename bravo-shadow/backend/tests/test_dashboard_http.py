from types import MappingProxyType

from fastapi.testclient import TestClient

from app.core.authentication import get_current_principal
from app.core.authorization import AuthenticatedPrincipal, CAPABILITIES
from app.core import authorization
from app.main import create_app


def configure_auth(application, profile="Admin"):
    async def principal():
        return AuthenticatedPrincipal(
            subject="google-test-subject",
            email="teste@example.com",
            profile=profile,
            account_status="Ativo",
        )
    application.dependency_overrides[get_current_principal] = principal


def test_dashboard_summary_requires_authentication():
    client = TestClient(create_app(storage_backend="memory"))
    assert client.get("/api/v1/dashboard/resumo").status_code == 401


def test_dashboard_summary_requires_dashboard_read_capability(monkeypatch):
    monkeypatch.setattr(
        authorization,
        "ROLE_CAPABILITIES",
        MappingProxyType({"Admin": frozenset(), "Operador": frozenset()}),
    )
    application = create_app(storage_backend="memory")
    configure_auth(application)
    client = TestClient(application)
    assert client.get("/api/v1/dashboard/resumo").status_code == 403


def test_dashboard_summary_returns_aggregates_only(monkeypatch):
    monkeypatch.setattr(
        authorization,
        "ROLE_CAPABILITIES",
        MappingProxyType({"Admin": CAPABILITIES, "Operador": frozenset()}),
    )
    application = create_app(storage_backend="memory")
    configure_auth(application)
    client = TestClient(application)
    response = client.get("/api/v1/dashboard/resumo")
    assert response.status_code == 200
    data = response.json()
    assert data["total_moradores"] == 0
    assert data["valor_receber"] == "0.00"
    assert "moradores" not in data
    assert "historicos" not in data
