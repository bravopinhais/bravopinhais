from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.core.authentication import get_current_principal
from app.core.authorization import (
    AuthenticatedPrincipal,
    require_capability_dependency,
)


def make_principal(profile: str = "Admin") -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(
        subject="google-test-subject",
        email="teste@example.com",
        profile=profile,
        account_status="Ativo",
    )


def build_test_client(principal: AuthenticatedPrincipal | None = None) -> TestClient:
    application = FastAPI()
    router = APIRouter()

    async def fake_authentication() -> AuthenticatedPrincipal:
        if principal is None:
            raise HTTPException(status_code=401, detail="Token obrigatório.")
        return principal

    application.dependency_overrides[get_current_principal] = fake_authentication

    @router.get(
        "/protected",
        dependencies=[Depends(require_capability_dependency("financeiro:read"))],
    )
    async def protected_resource():
        return {"ok": True}

    application.include_router(router)
    return TestClient(application)


def test_protected_route_returns_401_without_identity():
    response = build_test_client().get("/protected")
    assert response.status_code == 401


def test_protected_route_returns_403_without_capability():
    response = build_test_client(make_principal("Operador")).get("/protected")
    assert response.status_code == 403


def test_protected_route_returns_200_with_required_capability():
    response = build_test_client(make_principal("Admin")).get("/protected")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_protected_route_rejects_unknown_capability_even_for_admin():
    application = FastAPI()
    router = APIRouter()

    async def authenticated_admin() -> AuthenticatedPrincipal:
        return make_principal("Admin")

    application.dependency_overrides[get_current_principal] = authenticated_admin

    @router.get(
        "/protected-unknown",
        dependencies=[Depends(require_capability_dependency("financeiro:superuser"))],
    )
    async def protected_unknown():
        return {"ok": True}

    application.include_router(router)
    response = TestClient(application).get("/protected-unknown")
    assert response.status_code == 403
