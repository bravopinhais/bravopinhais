from fastapi.testclient import TestClient
import pytest

from app.core.storage import StorageConfigurationError, build_storage_services
from app.core.postgres_audit import PostgresAuditSink
from app.main import create_app


def test_postgres_mode_requires_explicit_connection_factory():
    with pytest.raises(StorageConfigurationError):
        create_app(storage_backend="postgres")


def test_postgres_mode_is_reported_without_opening_connection():
    calls = []

    def connection_factory():
        calls.append("opened")
        raise AssertionError("A conexão não deve abrir durante a criação da aplicação ou health check.")

    application = create_app(
        storage_backend="postgres",
        postgres_connection_factory=connection_factory,
    )

    with TestClient(application) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["storage"] == "postgres"
    assert calls == []



def test_postgres_storage_wires_audit_sink_without_opening_connection():
    calls = []

    def connection_factory():
        calls.append("opened")
        raise AssertionError("A conexão só deve abrir durante uma operação.")

    services = build_storage_services("postgres", connection_factory)

    assert isinstance(services.audit_sink, PostgresAuditSink)
    assert services.usuarios.audit_sink is services.audit_sink
    assert calls == []


def test_memory_storage_does_not_configure_persistent_audit_sink():
    services = build_storage_services("memory")

    assert services.audit_sink is None
    assert services.usuarios.audit_sink is None
