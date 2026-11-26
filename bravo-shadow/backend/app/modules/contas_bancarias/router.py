from fastapi import APIRouter, Request, status

from .schemas import ContaBancaria, ContaBancariaInput
from .service import ContasBancariasService

router = APIRouter(prefix="/api/v1/contas-bancarias", tags=["Contas Bancárias"])


def get_service(request: Request) -> ContasBancariasService:
    return request.app.state.services.contas_bancarias


@router.get("", response_model=list[ContaBancaria])
def list_accounts(request: Request) -> list[ContaBancaria]:
    return get_service(request).list()


@router.post("", response_model=ContaBancaria, status_code=status.HTTP_201_CREATED)
def create_account(request: Request, data: ContaBancariaInput) -> ContaBancaria:
    return get_service(request).create(data)


@router.put("/{item_id}", response_model=ContaBancaria)
def update_account(request: Request, item_id: str, data: ContaBancariaInput) -> ContaBancaria:
    return get_service(request).update(item_id, data)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(request: Request, item_id: str) -> None:
    get_service(request).delete(item_id)
