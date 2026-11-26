from fastapi import APIRouter, status

from .schemas import PlanoConta, PlanoContaInput
from .service import plano_contas_service

router = APIRouter(prefix="/api/v1/plano-contas", tags=["Plano de Contas"])


@router.get("", response_model=list[PlanoConta])
def list_accounts() -> list[PlanoConta]:
    return plano_contas_service.list()


@router.post("", response_model=PlanoConta, status_code=status.HTTP_201_CREATED)
def create_account(data: PlanoContaInput) -> PlanoConta:
    return plano_contas_service.create(data)


@router.put("/{item_id}", response_model=PlanoConta)
def update_account(item_id: str, data: PlanoContaInput) -> PlanoConta:
    return plano_contas_service.update(item_id, data)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(item_id: str) -> None:
    plano_contas_service.delete(item_id)
