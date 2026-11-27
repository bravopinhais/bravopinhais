from fastapi import APIRouter, Depends, Request

from app.core.authorization import require_capability_dependency
from .schemas import DREResumo
from .service import RelatoriosService

router = APIRouter(prefix="/api/v1/relatorios", tags=["Relatórios & DRE"])


def get_service(request: Request) -> RelatoriosService:
    return request.app.state.relatorios_service


@router.get(
    "/dre",
    response_model=DREResumo,
    dependencies=[Depends(require_capability_dependency("relatorios:read"))],
)
def read_dre(request: Request) -> DREResumo:
    return get_service(request).dre()
