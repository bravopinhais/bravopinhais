from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status

from app.core.authorization import require_capability_dependency

from app.core.etag import format_etag, parse_if_match
from .schemas import FinanceiroInput, FinanceiroTitulo
from .service import FinanceiroService

router = APIRouter(prefix="/api/v1/financeiro", tags=["Financeiro"])

read_access = Depends(require_capability_dependency("financeiro:read"))
create_access = Depends(require_capability_dependency("financeiro:create"))
update_access = Depends(require_capability_dependency("financeiro:update"))
delete_access = Depends(require_capability_dependency("financeiro:delete"))


def get_service(request: Request) -> FinanceiroService:
    return request.app.state.services.financeiro


@router.get("", response_model=list[FinanceiroTitulo], dependencies=[read_access])
def list_titles(request: Request) -> list[FinanceiroTitulo]:
    return get_service(request).list()


@router.post("", response_model=FinanceiroTitulo, status_code=status.HTTP_201_CREATED, dependencies=[create_access])
def create_title(
    data: FinanceiroInput,
    request: Request,
    _principal=Depends(require_capability_dependency("financeiro:create")),
):
    # Fail closed: ainda não há auditoria atômica junto da mutação financeira.
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Inclusão financeira bloqueada até a auditoria transacional estar integrada.",
    )


@router.put("/{item_id}", response_model=FinanceiroTitulo, dependencies=[update_access])
def update_title(
    item_id: str,
    data: FinanceiroInput,
    request: Request,
    response: Response,
    if_match: str | None = Header(default=None, alias="If-Match"),
    _principal=Depends(require_capability_dependency("financeiro:update")),
):
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Edição financeira bloqueada até a auditoria transacional estar integrada.",
    )


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[delete_access])
def delete_title(
    item_id: str,
    request: Request,
    _principal=Depends(require_capability_dependency("financeiro:delete")),
) -> None:
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Exclusão financeira bloqueada até a auditoria transacional estar integrada.",
    )
