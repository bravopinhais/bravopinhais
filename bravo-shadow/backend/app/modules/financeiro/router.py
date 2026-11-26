from fastapi import APIRouter, status

from .schemas import FinanceiroInput, FinanceiroTitulo
from .service import financeiro_service

router = APIRouter(prefix="/api/v1/financeiro", tags=["Financeiro"])


@router.get("", response_model=list[FinanceiroTitulo])
def list_titles() -> list[FinanceiroTitulo]:
    return financeiro_service.list()


@router.post("", response_model=FinanceiroTitulo, status_code=status.HTTP_201_CREATED)
def create_title(data: FinanceiroInput) -> FinanceiroTitulo:
    return financeiro_service.create(data)


@router.put("/{item_id}", response_model=FinanceiroTitulo)
def update_title(item_id: str, data: FinanceiroInput) -> FinanceiroTitulo:
    return financeiro_service.update(item_id, data)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_title(item_id: str) -> None:
    financeiro_service.delete(item_id)
