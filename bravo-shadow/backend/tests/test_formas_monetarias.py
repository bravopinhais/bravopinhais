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


def test_admin_is_denied_all_formas_monetarias_actions_until_matrix_approval():
    client = build_client("Admin")
    assert client.get("/api/v1/formas-monetarias").status_code == 403
    assert client.post("/api/v1/formas-monetarias", json={"nome": "Boleto"}).status_code == 403
    assert client.put("/api/v1/formas-monetarias/1", json={"nome": "PIX"}).status_code == 403
    assert client.delete("/api/v1/formas-monetarias/1").status_code == 403


def test_operator_is_denied_all_formas_monetarias_actions_until_matrix_approval():
    client = build_client("Operador")
    assert client.get("/api/v1/formas-monetarias").status_code == 403
    assert client.post("/api/v1/formas-monetarias", json={"nome": "Boleto"}).status_code == 403
    assert client.put("/api/v1/formas-monetarias/1", json={"nome": "PIX"}).status_code == 403
    assert client.delete("/api/v1/formas-monetarias/1").status_code == 403


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
