from fastapi.testclient import TestClient

from app.main import create_app


def test_create_and_get_profile_by_email():
    client = TestClient(create_app())
    response = client.post("/api/v1/usuarios", json={
        "email": "  ADMIN@EXAMPLE.COM ", "nome": "Administrador",
        "loja": "Condomínio Bravo", "cargo": "Síndico", "perfil": "Admin"
    })
    assert response.status_code == 201
    user = response.json()
    assert user["email"] == "admin@example.com"
    assert client.get("/api/v1/usuarios/" + user["id"]).json()["perfil"] == "Admin"


def test_email_is_unique_case_insensitively():
    client = TestClient(create_app())
    payload = {"email": "user@example.com", "nome": "Pessoa", "cargo": "Conselho"}
    assert client.post("/api/v1/usuarios", json=payload).status_code == 201
    payload["email"] = "USER@example.com"
    assert client.post("/api/v1/usuarios", json=payload).status_code == 409


def test_update_and_delete_profile():
    client = TestClient(create_app())
    payload = {"email": "user@example.com", "nome": "Pessoa", "cargo": "Conselho"}
    user = client.post("/api/v1/usuarios", json=payload).json()
    payload["status"] = "Inativo"
    assert client.put("/api/v1/usuarios/" + user["id"], json=payload).json()["status"] == "Inativo"
    assert client.delete("/api/v1/usuarios/" + user["id"]).status_code == 204
    assert client.get("/api/v1/usuarios/" + user["id"]).status_code == 404


def test_password_fields_are_rejected():
    client = TestClient(create_app())
    payload = {"email": "user@example.com", "nome": "Pessoa", "cargo": "Conselho", "senhaHash": "legacy"}
    assert client.post("/api/v1/usuarios", json=payload).status_code == 422


def test_user_profiles_are_isolated_between_app_instances():
    first, second = TestClient(create_app()), TestClient(create_app())
    first.post("/api/v1/usuarios", json={"email": "admin@example.com", "nome": "Admin", "cargo": "Síndico"})
    assert len(first.get("/api/v1/usuarios").json()) == 1
    assert second.get("/api/v1/usuarios").json() == []
