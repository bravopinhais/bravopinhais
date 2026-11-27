from fastapi import APIRouter, Depends, Request

from app.core.authorization import AuthenticatedPrincipal, require_capability_dependency
from .schemas import ModuloEstado, ModuloEstadoUpdate, ModulosAcaoEmMassa
from .service import ConfiguracoesService

router = APIRouter(prefix="/api/v1/configuracoes", tags=["Configurações"])


def get_service(request: Request) -> ConfiguracoesService:
    return request.app.state.services.configuracoes


@router.get("/modulos", response_model=list[ModuloEstado])
def list_modules(
    request: Request,
    _principal: AuthenticatedPrincipal = Depends(
        require_capability_dependency("configuracoes:read")
    ),
):
    return get_service(request).list_modules()


@router.patch("/modulos/{key}", response_model=ModuloEstado)
def update_module(
    request: Request,
    key: str,
    data: ModuloEstadoUpdate,
    principal: AuthenticatedPrincipal = Depends(
        require_capability_dependency("configuracoes:update")
    ),
):
    return get_service(request).set_module(
        key, data.ativo, actor=principal,
        request_id=getattr(request.state, "request_id", None),
    )


@router.post("/modulos/acao-em-massa", response_model=list[ModuloEstado])
def bulk_update_modules(
    request: Request,
    data: ModulosAcaoEmMassa,
    principal: AuthenticatedPrincipal = Depends(
        require_capability_dependency("configuracoes:update")
    ),
):
    return get_service(request).apply_bulk(
        data.acao, actor=principal,
        request_id=getattr(request.state, "request_id", None),
    )
