from fastapi import APIRouter, Depends, Header, Request, Response, status

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
def create_title(data: FinanceiroInput, request: Request, response: Response):
    item = get_service(request).create(data)
    response.headers["ETag"] = format_etag(item.version)
    return item


@router.put("/{item_id}", response_model=FinanceiroTitulo, dependencies=[update_access])
def update_title(
    item_id: str,
    data: FinanceiroInput,
    request: Request,
    response: Response,
    if_match: str | None = Header(default=None, alias="If-Match"),
):
    expected_version = parse_if_match(if_match)
    item = get_service(request).update(item_id, data, expected_version)
    response.headers["ETag"] = format_etag(item.version)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[delete_access])
def delete_title(item_id: str, request: Request) -> None:
    get_service(request).delete(item_id)
