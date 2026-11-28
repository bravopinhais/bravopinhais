from dataclasses import asdict

from fastapi import APIRouter, Depends, Request

from app.core.authorization import AuthenticatedPrincipal, require_capability_dependency
from app.core.read_audit import audit_read

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard"])


@router.get(
    "/resumo",

)
def dashboard_summary(
    request: Request,
    principal: AuthenticatedPrincipal = Depends(require_capability_dependency("dashboard:read")),
):
    audit_read(request, request.app.state.services.financeiro, principal, "dashboard:summary", "dashboard")
    return asdict(request.app.state.dashboard_service.summary())
