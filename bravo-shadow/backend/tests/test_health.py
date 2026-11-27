from fastapi.testclient import TestClient

from app.core.authentication import get_current_principal
from app.core.authorization import AuthenticatedPrincipal, CAPABILITIES
from app.main import app, create_app


client = TestClient(app)


def test_health_endpoint_returns_ok() -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "bravo-shadow-api",
        "version": "0.1.0",
        "storage": "memory",
    }


def test_postgres_mode_requires_database_url_when_factory_is_not_injected(monkeypatch) -> None:
    import pytest

    from app.core.storage import StorageConfigurationError

    monkeypatch.delenv("BRAVO_DATABASE_URL", raising=False)
    with pytest.raises(StorageConfigurationError, match="BRAVO_DATABASE_URL"):
        create_app(storage_backend="postgres")


def test_postgres_mode_accepts_injected_factory_without_connecting() -> None:
    calls = []

    def connection_factory():
        calls.append("connect")
        raise AssertionError("A fábrica não deve ser chamada durante a configuração.")

    postgres_app = create_app(
        storage_backend="postgres",
        postgres_connection_factory=connection_factory,
    )
    assert postgres_app.state.storage_backend == "postgres"
    assert calls == []



def test_unknown_storage_backend_is_rejected() -> None:
    import pytest

    from app.core.storage import StorageConfigurationError

    with pytest.raises(StorageConfigurationError, match="BRAVO_STORAGE_BACKEND"):
        create_app(storage_backend="automatic")


def test_frontend_is_served_from_root() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "Bravo Shadow" in response.text
    assert 'id="navigation"' in response.text


def test_frontend_exposes_first_api_integrated_module() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert 'id="forma-form"' in response.text
    assert '"/formas-monetarias"' in response.text
    assert "Carregando dados da API" in response.text



def test_app_instances_do_not_share_pilot_storage() -> None:
    from app.modules.formas_monetarias.schemas import FormaMonetariaInput

    first_app = create_app(storage_backend="memory")
    second_app = create_app(storage_backend="memory")
    first_service = first_app.state.services.formas_monetarias
    second_service = second_app.state.services.formas_monetarias

    first_service.create(FormaMonetariaInput(nome="Dinheiro - app 1", multaPct=2))
    assert len(first_service.list()) == 1
    assert second_service.list() == []

    second_service.create(FormaMonetariaInput(nome="Dinheiro - app 2", multaPct=2))
    assert len(first_service.list()) == 1
    assert len(second_service.list()) == 1


def test_app_instances_keep_financial_services_separate(monkeypatch) -> None:
    from types import MappingProxyType
    from app.core import authorization

    monkeypatch.setattr(authorization, "ROLE_CAPABILITIES", MappingProxyType({"Admin": CAPABILITIES, "Operador": frozenset()}))
    first_app = create_app(storage_backend="memory")
    second_app = create_app(storage_backend="memory")
    async def authenticated_admin() -> AuthenticatedPrincipal:
        return AuthenticatedPrincipal(subject="google-test-subject", email="teste@example.com", profile="Admin", account_status="Ativo")

    first_app.dependency_overrides[get_current_principal] = authenticated_admin
    second_app.dependency_overrides[get_current_principal] = authenticated_admin
    first_client = TestClient(first_app)
    second_client = TestClient(second_app)

    response = first_client.post(
        "/api/v1/plano-contas",
        json={"codigo": "1.1", "nome": "Receitas", "tipo": "Receita"},
    )
    assert response.status_code == 201
    assert len(first_client.get("/api/v1/plano-contas").json()) == 1
    assert second_client.get("/api/v1/plano-contas").json() == []

def test_request_id_is_generated_by_server_and_returned_in_response():
    import re

    response = client.get("/api/v1/health")

    request_id = response.headers.get("X-Request-ID")
    assert request_id is not None
    assert re.fullmatch(r"req_[0-9a-f]{32}", request_id)


def test_client_cannot_choose_server_request_id():
    response = client.get(
        "/api/v1/health",
        headers={"X-Request-ID": "req_forged-by-client"},
    )

    assert response.headers["X-Request-ID"] != "req_forged-by-client"
    assert response.headers["X-Request-ID"].startswith("req_")


def test_each_request_receives_a_distinct_request_id():
    first = client.get("/api/v1/health")
    second = client.get("/api/v1/health")

    assert first.headers["X-Request-ID"] != second.headers["X-Request-ID"]
