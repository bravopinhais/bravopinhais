from fastapi.testclient import TestClient

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


def test_postgres_mode_requires_explicit_connection_factory() -> None:
    import pytest

    from app.core.storage import StorageConfigurationError

    with pytest.raises(StorageConfigurationError, match="connection_factory explícita"):
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

    # Restaura o estado global usado pela aplicação padrão de testes.
    create_app(storage_backend="memory")


def test_unknown_storage_backend_is_rejected() -> None:
    import pytest

    from app.core.storage import StorageConfigurationError

    with pytest.raises(StorageConfigurationError, match="BRAVO_STORAGE_BACKEND"):
        create_app(storage_backend="automatic")
