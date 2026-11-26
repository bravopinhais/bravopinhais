from fastapi.testclient import TestClient
import pytest

from app.core.storage import StorageConfigurationError, configure_storage
from app.main import create_app


def test_postgres_mode_requires_explicit_connection_factory():
    with pytest.raises(StorageConfigurationError):
        create_app(storage_backend="postgres")


def test_postgres_mode_is_reported_without_opening_connection():
    calls = []

    def connection_factory():
        calls.append("opened")
        raise AssertionError("A conexão não deve abrir durante a criação da aplicação ou health check.")

    try:
        application = create_app(
            storage_backend="postgres",
            postgres_connection_factory=connection_factory,
        )

        with TestClient(application) as client:
            response = client.get("/api/v1/health")

        assert response.status_code == 200
        assert response.json()["storage"] == "postgres"
        assert calls == []
    finally:
        configure_storage("memory")
