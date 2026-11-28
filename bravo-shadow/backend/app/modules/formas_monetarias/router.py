from fastapi import APIRouter, Depends, Request, status

from app.core.authorization import AuthenticatedPrincipal, require_capability_dependency
from app.core.read_audit import audit_read

from .schemas import FormaMonetaria, FormaMonetariaInput
from .service import FormasMonetariasService

router = APIRouter(prefix="/api/v1/formas-monetarias", tags=["Formas Monetárias"])


def get_service(request: Request) -> FormasMonetariasService:
    return request.app.state.services.formas_monetarias


@router.get("", response_model=list[FormaMonetaria])
def list_forms(
    request: Request,
    _principal: AuthenticatedPrincipal = Depends(require_capability_dependency("formas_monetarias:read")),
) -> list[FormaMonetaria]:
    service = get_service(request)
    audit_read(request, service, _principal, "formas_monetarias:list", "forma_monetaria")
    return service.list()


@router.post("", response_model=FormaMonetaria, status_code=status.HTTP_201_CREATED)
def create_form(
    data: FormaMonetariaInput,
    request: Request,
    principal: AuthenticatedPrincipal = Depends(require_capability_dependency("formas_monetarias:create")),
) -> FormaMonetaria:
    return get_service(request).create(data, actor=principal, request_id=getattr(request.state, "request_id", None))


@router.put("/{item_id}", response_model=FormaMonetaria)
def update_form(
    item_id: str,
    data: FormaMonetariaInput,
    request: Request,
    principal: AuthenticatedPrincipal = Depends(require_capability_dependency("formas_monetarias:update")),
) -> FormaMonetaria:
    return get_service(request).update(item_id, data, actor=principal, request_id=getattr(request.state, "request_id", None))


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_form(
    item_id: str,
    request: Request,
    principal: AuthenticatedPrincipal = Depends(require_capability_dependency("formas_monetarias:delete")),
) -> None:
    get_service(request).delete(item_id, actor=principal, request_id=getattr(request.state, "request_id", None))
