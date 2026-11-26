from fastapi import APIRouter, status

from .schemas import ContaBancaria, ContaBancariaInput
from .service import contas_bancarias_service

router = APIRouter(prefix="/api/v1/contas-bancarias", tags=["Contas Bancárias"])


@router.get("", response_model=list[ContaBancaria])
def list_accounts() -> list[ContaBancaria]:
    return contas_bancarias_service.list()


@router.post("", response_model=ContaBancaria, status_code=status.HTTP_201_CREATED)
def create_account(data: ContaBancariaInput) -> ContaBancaria:
    return contas_bancarias_service.create(data)


@router.put("/{item_id}", response_model=ContaBancaria)
def update_account(item_id: str, data: ContaBancariaInput) -> ContaBancaria:
    return contas_bancarias_service.update(item_id, data)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(item_id: str) -> None:
    contas_bancarias_service.delete(item_id)
