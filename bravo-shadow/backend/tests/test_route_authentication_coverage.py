"""Regressão: todas as rotas de negócio da API exigem identidade Google."""

from fastapi.routing import APIRoute

from app.core.authentication import get_current_principal
from app.core.authorization import CAPABILITIES
from app.main import create_app


def _depends_on_google_identity(dependant) -> bool:
    """Percorre dependências aninhadas do FastAPI, sem executar handlers."""
    if dependant.call is get_current_principal:
        return True
    return any(
        _depends_on_google_identity(child)
        for child in dependant.dependencies
    )


def test_every_business_api_route_requires_google_identity():
    application = create_app(storage_backend="memory")
    business_routes = [
        route
        for route in application.routes
        if isinstance(route, APIRoute)
        and route.path.startswith("/api/v1/")
        and route.path != "/api/v1/health"
    ]

    assert business_routes, "A API deve registrar rotas de negócio para auditar."

    unprotected = [
        f"{','.join(sorted(route.methods or []))} {route.path}"
        for route in business_routes
        if not _depends_on_google_identity(route.dependant)
    ]

    assert not unprotected, (
        "Rotas de negócio sem dependência de identidade Google: "
        + "; ".join(unprotected)
    )



def _has_capability_gate(dependant) -> bool:
    """Identifica uma barreira de capacidade em qualquer nível da rota."""
    capability = getattr(dependant.call, "__bravo_required_capability__", None)
    if capability in CAPABILITIES:
        return True
    return any(_has_capability_gate(child) for child in dependant.dependencies)


def test_every_business_api_route_has_capability_gate_or_is_identity_endpoint():
    application = create_app(storage_backend="memory")
    business_routes = [
        route
        for route in application.routes
        if isinstance(route, APIRoute)
        and route.path.startswith("/api/v1/")
        and route.path != "/api/v1/health"
    ]

    # /auth/me apenas confirma a identidade já validada; não concede acesso
    # a dados ou operações de negócio. Todas as demais rotas exigem capacidade.
    unguarded = [
        f"{','.join(sorted(route.methods or []))} {route.path}"
        for route in business_routes
        if route.path != "/api/v1/auth/me"
        and not _has_capability_gate(route.dependant)
    ]

    assert not unguarded, (
        "Rotas de negócio sem barreira de capacidade: " + "; ".join(unguarded)
    )
