from fastapi import APIRouter, Depends, Request, status

from app.core.authorization import AuthenticatedPrincipal, require_capability_dependency
from .schemas import EstoqueInput, EstoqueItem
from .service import EstoqueService

router = APIRouter(prefix="/api/v1/estoque", tags=["Estoque e Inventário"])


def get_service(request: Request) -> EstoqueService:
    return request.app.state.services.estoque


@router.get("", response_model=list[EstoqueItem], dependencies=[Depends(require_capability_dependency("estoque:read"))])
def list_items(request: Request):
    return get_service(request).list()


@router.post("", response_model=EstoqueItem, status_code=status.HTTP_201_CREATED)
def create_item(
    data: EstoqueInput,
    request: Request,
    _principal: AuthenticatedPrincipal = Depends(require_capability_dependency("estoque:create")),
):
    return get_service(request).create(
        data, actor=_principal, request_id=getattr(request.state, "request_id", None)
    )


@router.put("/{item_id}", response_model=EstoqueItem)
def update_item(
    item_id: str,
    data: EstoqueInput,
    request: Request,
    _principal: AuthenticatedPrincipal = Depends(require_capability_dependency("estoque:update")),
):
    return get_service(request).update(
        item_id, data, actor=_principal, request_id=getattr(request.state, "request_id", None)
    )


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(
    item_id: str,
    request: Request,
    _principal: AuthenticatedPrincipal = Depends(require_capability_dependency("estoque:delete")),
):
    get_service(request).delete(
        item_id, actor=_principal, request_id=getattr(request.state, "request_id", None)
    )
