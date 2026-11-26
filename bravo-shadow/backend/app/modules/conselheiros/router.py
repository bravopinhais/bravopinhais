from fastapi import APIRouter, Depends, Request, status

from app.core.authorization import AuthenticatedPrincipal, require_capability_dependency

from .schemas import Conselheiro, ConselheiroInput
from .service import ConselheirosService

router = APIRouter(prefix="/api/v1/conselheiros", tags=["Conselheiros"])


def get_service(request: Request) -> ConselheirosService:
    return request.app.state.services.conselheiros


@router.get("", response_model=list[Conselheiro])
def list_council(
    request: Request,
    _principal: AuthenticatedPrincipal = Depends(require_capability_dependency("conselheiros:read")),
) -> list[Conselheiro]:
    return get_service(request).list()


@router.post("", response_model=Conselheiro, status_code=status.HTTP_201_CREATED)
def create_council_member(
    request: Request,
    data: ConselheiroInput,
    _principal: AuthenticatedPrincipal = Depends(require_capability_dependency("conselheiros:create")),
) -> Conselheiro:
    return get_service(request).create(data)


@router.put("/{item_id}", response_model=Conselheiro)
def update_council_member(
    request: Request,
    item_id: str,
    data: ConselheiroInput,
    _principal: AuthenticatedPrincipal = Depends(require_capability_dependency("conselheiros:update")),
) -> Conselheiro:
    return get_service(request).update(item_id, data)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_council_member(
    request: Request,
    item_id: str,
    _principal: AuthenticatedPrincipal = Depends(require_capability_dependency("conselheiros:delete")),
) -> None:
    get_service(request).delete(item_id)
