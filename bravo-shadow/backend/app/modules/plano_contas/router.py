from fastapi import APIRouter, Header, Response, status

from app.core.etag import format_etag, parse_if_match
from .schemas import PlanoConta, PlanoContaInput
from .service import plano_contas_service

router = APIRouter(prefix="/api/v1/plano-contas", tags=["Plano de Contas"])


@router.get("", response_model=list[PlanoConta])
def list_accounts() -> list[PlanoConta]:
    return plano_contas_service.list()


@router.post("", response_model=PlanoConta, status_code=status.HTTP_201_CREATED)
def create_account(data: PlanoContaInput, response: Response):
    item = plano_contas_service.create(data)
    response.headers["ETag"] = format_etag(item.version)
    return item


@router.put("/{item_id}", response_model=PlanoConta)
def update_account(
    item_id: str,
    data: PlanoContaInput,
    response: Response,
    if_match: str | None = Header(default=None, alias="If-Match"),
):
    expected_version = parse_if_match(if_match)
    item = plano_contas_service.update(item_id, data, expected_version)
    response.headers["ETag"] = format_etag(item.version)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(item_id: str) -> None:
    plano_contas_service.delete(item_id)
