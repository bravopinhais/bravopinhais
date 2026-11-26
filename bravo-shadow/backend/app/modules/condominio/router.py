from fastapi import APIRouter, Depends, Request

from app.core.authorization import AuthenticatedPrincipal, require_capability_dependency
from .schemas import Condominio, CondominioPatch
from .service import CondominioService

router = APIRouter(prefix="/api/v1/condominio", tags=["Condomínio"])


def get_service(request: Request) -> CondominioService:
    return request.app.state.services.condominio


@router.get("", response_model=Condominio)
def get_condominium(
    request: Request,
    _principal: AuthenticatedPrincipal = Depends(require_capability_dependency("condominio:read")),
) -> Condominio:
    return get_service(request).get()


@router.put("", response_model=Condominio)
def update_condominium(
    request: Request,
    data: CondominioPatch,
    _principal: AuthenticatedPrincipal = Depends(require_capability_dependency("condominio:update")),
) -> Condominio:
    return get_service(request).update(data)
