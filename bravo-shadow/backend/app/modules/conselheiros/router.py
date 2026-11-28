from fastapi import APIRouter, Depends, Request, status

from app.core.authorization import AuthenticatedPrincipal, require_capability_dependency
from app.core.read_audit import audit_read

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
    service = get_service(request)
    audit_read(request, service, _principal, "conselheiros:list", "conselheiro")
    return service.list()


@router.post("", response_model=Conselheiro, status_code=status.HTTP_201_CREATED)
def create_council_member(
    request: Request,
    data: ConselheiroInput,
    principal: AuthenticatedPrincipal = Depends(require_capability_dependency("conselheiros:create")),
) -> Conselheiro:
    return get_service(request).create(data, actor=principal, request_id=getattr(request.state, "request_id", None))


@router.put("/{item_id}", response_model=Conselheiro)
def update_council_member(
    request: Request,
    item_id: str,
    data: ConselheiroInput,
    principal: AuthenticatedPrincipal = Depends(require_capability_dependency("conselheiros:update")),
) -> Conselheiro:
    return get_service(request).update(item_id, data, actor=principal, request_id=getattr(request.state, "request_id", None))


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_council_member(
    request: Request,
    item_id: str,
    principal: AuthenticatedPrincipal = Depends(require_capability_dependency("conselheiros:delete")),
) -> None:
    get_service(request).delete(item_id, actor=principal, request_id=getattr(request.state, "request_id", None))
