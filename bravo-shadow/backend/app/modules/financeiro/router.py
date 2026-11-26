from fastapi import APIRouter, Header, Response, status

from app.core.etag import format_etag, parse_if_match
from .schemas import FinanceiroInput, FinanceiroTitulo
from .service import financeiro_service

router = APIRouter(prefix="/api/v1/financeiro", tags=["Financeiro"])


@router.get("", response_model=list[FinanceiroTitulo])
def list_titles() -> list[FinanceiroTitulo]:
    return financeiro_service.list()


@router.post("", response_model=FinanceiroTitulo, status_code=status.HTTP_201_CREATED)
def create_title(data: FinanceiroInput, response: Response):
    item = financeiro_service.create(data)
    response.headers["ETag"] = format_etag(item.version)
    return item


@router.put("/{item_id}", response_model=FinanceiroTitulo)
def update_title(
    item_id: str,
    data: FinanceiroInput,
    response: Response,
    if_match: str | None = Header(default=None, alias="If-Match"),
):
    expected_version = parse_if_match(if_match)
    item = financeiro_service.update(item_id, data, expected_version)
    response.headers["ETag"] = format_etag(item.version)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_title(item_id: str) -> None:
    financeiro_service.delete(item_id)
