from fastapi import APIRouter, Depends, Request, status

from app.core.authorization import AuthenticatedPrincipal, require_capability_dependency
from .schemas import Acerto, AcertoInput
from .service import AcertosEstoqueService

router = APIRouter(prefix="/api/v1/acertos-estoque", tags=["Acertos de Estoque"])


def get_service(request: Request) -> AcertosEstoqueService:
    return request.app.state.services.acertos_estoque


@router.get(
    "",
    response_model=list[Acerto],
    dependencies=[Depends(require_capability_dependency("acertos_estoque:read"))],
)
def list_adjustments(request: Request):
    return get_service(request).list()


@router.post(
    "",
    response_model=Acerto,
    status_code=status.HTTP_201_CREATED,
)
def create_adjustment(
    data: AcertoInput,
    request: Request,
    _principal: AuthenticatedPrincipal = Depends(require_capability_dependency("acertos_estoque:create")),
):
    return get_service(request).create(
        data, actor=_principal, request_id=getattr(request.state, "request_id", None)
    )
