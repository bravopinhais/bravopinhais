from fastapi import APIRouter, Depends, Header, Request, Response, status

from app.core.authorization import AuthenticatedPrincipal, require_capability_dependency
from app.core.read_audit import audit_read
from app.core.etag import format_etag, parse_if_match
from .schemas import PlanoConta, PlanoContaInput
from .service import PlanoContasService

router = APIRouter(prefix="/api/v1/plano-contas", tags=["Plano de Contas"])


def get_service(request: Request) -> PlanoContasService:
    return request.app.state.services.plano_contas


@router.get("", response_model=list[PlanoConta])
def list_accounts(
    request: Request,
    _principal: AuthenticatedPrincipal = Depends(require_capability_dependency("plano_contas:read")),
) -> list[PlanoConta]:
    service = get_service(request)
    audit_read(request, service, _principal, "plano_contas:list", "plano_conta")
    return service.list()


@router.post("", response_model=PlanoConta, status_code=status.HTTP_201_CREATED)
def create_account(
    data: PlanoContaInput,
    request: Request,
    response: Response,
    _principal: AuthenticatedPrincipal = Depends(require_capability_dependency("plano_contas:create")),
):
    item = get_service(request).create(
        data, actor=_principal, request_id=getattr(request.state, "request_id", None)
    )
    response.headers["ETag"] = format_etag(item.version)
    return item


@router.put("/{item_id}", response_model=PlanoConta)
def update_account(
    item_id: str,
    data: PlanoContaInput,
    request: Request,
    response: Response,
    if_match: str | None = Header(default=None, alias="If-Match"),
    _principal: AuthenticatedPrincipal = Depends(require_capability_dependency("plano_contas:update")),
):
    expected_version = parse_if_match(if_match)
    item = get_service(request).update(
        item_id, data, expected_version,
        actor=_principal, request_id=getattr(request.state, "request_id", None),
    )
    response.headers["ETag"] = format_etag(item.version)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    item_id: str,
    request: Request,
    _principal: AuthenticatedPrincipal = Depends(require_capability_dependency("plano_contas:delete")),
) -> None:
    get_service(request).delete(
        item_id, actor=_principal, request_id=getattr(request.state, "request_id", None)
    )
