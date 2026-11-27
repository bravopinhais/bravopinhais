"""Regressão: todas as rotas de negócio da API exigem identidade Google."""

from fastapi.routing import APIRoute

from app.core.authentication import get_current_principal
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
