from fastapi.testclient import TestClient

from app.main import create_app
from app.modules.usuarios.schemas import UsuarioInput


def add_user(application, email: str, profile: str = "Admin"):
    return application.state.services.usuarios.create(
        UsuarioInput(
            email=email,
            nome="Usuário de teste",
            loja="Bravo Shadow",
            cargo="Gestor",
            perfil=profile,
            status="Ativo",
        )
    )


def client_with_identity(profile: str = "Admin", email: str = "admin@example.com"):
    application = create_app(storage_backend="memory")
    application.state.google_token_verifier = lambda token: {
        "sub": f"google-{email}",
        "email": email,
        "email_verified": True,
    }
    add_user(application, email, profile)
    return application, TestClient(application)


def auth_headers():
    return {"Authorization": "Bearer token-de-teste"}


def test_user_management_requires_google_identity():
    application = create_app(storage_backend="memory")
    response = TestClient(application).get("/api/v1/usuarios")
    assert response.status_code == 401


def test_operator_cannot_list_users():
    application, client = client_with_identity("Operador", "operador@example.com")
    response = client.get("/api/v1/usuarios", headers=auth_headers())
    assert response.status_code == 403


def test_admin_cannot_change_own_profile_or_status():
    application, client = client_with_identity()
    current = application.state.services.usuarios.list()[0]
    response = client.put(
        f"/api/v1/usuarios/{current.id}",
        headers=auth_headers(),
        json={
            "email": current.email,
            "nome": current.nome,
            "loja": current.loja,
            "cargo": current.cargo,
            "perfil": "Operador",
            "status": "Ativo",
        },
    )
    assert response.status_code == 403


def test_admin_cannot_change_own_email():
    application, client = client_with_identity()
    current = application.state.services.usuarios.list()[0]
    response = client.put(
        f"/api/v1/usuarios/{current.id}",
        headers=auth_headers(),
        json={
            "email": "outro@example.com",
            "nome": current.nome,
            "loja": current.loja,
            "cargo": current.cargo,
            "perfil": current.perfil,
            "status": current.status,
        },
    )
    assert response.status_code == 403


def test_admin_can_update_another_user():
    application, client = client_with_identity()
    target = add_user(application, "operador@example.com", "Operador")
    response = client.put(
        f"/api/v1/usuarios/{target.id}",
        headers=auth_headers(),
        json={
            "email": target.email,
            "nome": "Operador atualizado",
            "loja": target.loja,
            "cargo": target.cargo,
            "perfil": "Operador",
            "status": "Ativo",
        },
    )
    assert response.status_code == 200
    assert response.json()["nome"] == "Operador atualizado"


def test_admin_cannot_delete_own_user():
    application, client = client_with_identity()
    current = application.state.services.usuarios.list()[0]
    response = client.delete(
        f"/api/v1/usuarios/{current.id}",
        headers=auth_headers(),
    )
    assert response.status_code == 403


def test_admin_can_create_another_admin():
    application, client = client_with_identity()
    response = client.post(
        "/api/v1/usuarios",
        headers=auth_headers(),
        json={
            "email": "novo-admin@example.com",
            "nome": "Novo administrador",
            "loja": "Bravo Shadow",
            "cargo": "Gestor",
            "perfil": "Admin",
            "status": "Ativo",
        },
    )
    assert response.status_code == 201
    assert response.json()["perfil"] == "Admin"
