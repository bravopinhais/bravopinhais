from fastapi import APIRouter, Depends, Request

from app.core.authorization import AuthenticatedPrincipal, require_capability_dependency
from app.core.read_audit import audit_read
from .schemas import DREResumo
from .service import RelatoriosService

router = APIRouter(prefix="/api/v1/relatorios", tags=["Relatórios & DRE"])


def get_service(request: Request) -> RelatoriosService:
    return request.app.state.relatorios_service


@router.get(
    "/dre",
    response_model=DREResumo,

)
def read_dre(
    request: Request,
    principal: AuthenticatedPrincipal = Depends(require_capability_dependency("relatorios:read")),
) -> DREResumo:
    audit_read(request, request.app.state.services.financeiro, principal, "relatorios:dre", "relatorio")
    return get_service(request).dre()
