from __future__ import annotations

import importlib.util
from pathlib import Path

from fastapi.testclient import TestClient


def load_vercel_entrypoint(monkeypatch, configured=None):
    configured = configured or {}
    for name in ("BRAVO_STORAGE_BACKEND", "BRAVO_DATABASE_URL", "GOOGLE_CLIENT_ID"):
        monkeypatch.delenv(name, raising=False)
    for name, value in configured.items():
        monkeypatch.setenv(name, value)

    repository_root = Path(__file__).resolve().parents[3]
    entrypoint = repository_root / "main.py"
    spec = importlib.util.spec_from_file_location("bravo_vercel_entrypoint_test", entrypoint)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_vercel_entrypoint_fails_closed_without_server_configuration(monkeypatch):
    module = load_vercel_entrypoint(monkeypatch)

    with TestClient(module.app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "blocked"
    assert payload["storage"] == "not-configured"
    assert set(payload["missing_configuration"]) == {
        "BRAVO_STORAGE_BACKEND",
        "BRAVO_DATABASE_URL",
        "GOOGLE_CLIENT_ID",
    }


def test_vercel_entrypoint_never_executes_api_operations_when_unconfigured(monkeypatch):
    module = load_vercel_entrypoint(monkeypatch)

    with TestClient(module.app) as client:
        response = client.post("/api/v1/financeiro", json={"valor": 123})

    assert response.status_code == 503
    assert "Nenhuma operação foi executada" in response.json()["detail"]


def test_vercel_entrypoint_serves_shadow_frontend_without_database(monkeypatch):
    module = load_vercel_entrypoint(monkeypatch)

    with TestClient(module.app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "Bravo Shadow" in response.text



def test_vercel_entrypoint_stays_blocked_when_only_some_settings_exist(monkeypatch):
    module = load_vercel_entrypoint(
        monkeypatch,
        {
            "BRAVO_STORAGE_BACKEND": "postgres",
            "GOOGLE_CLIENT_ID": "synthetic-client-id.apps.googleusercontent.com",
        },
    )

    with TestClient(module.app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 503
    assert response.json()["missing_configuration"] == ["BRAVO_DATABASE_URL"]


def test_vercel_entrypoint_rejects_memory_storage_even_with_other_settings(monkeypatch):
    module = load_vercel_entrypoint(
        monkeypatch,
        {
            "BRAVO_STORAGE_BACKEND": "memory",
            "BRAVO_DATABASE_URL": "postgresql://synthetic.invalid/bravo",
            "GOOGLE_CLIENT_ID": "synthetic-client-id.apps.googleusercontent.com",
        },
    )

    with TestClient(module.app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 503
    assert response.json()["missing_configuration"] == ["BRAVO_STORAGE_BACKEND"]
