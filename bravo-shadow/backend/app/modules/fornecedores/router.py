from fastapi import APIRouter, status
from .schemas import Fornecedor, FornecedorInput
from .service import fornecedores_service

router = APIRouter(prefix="/api/v1/fornecedores", tags=["Fornecedores"])

@router.get("", response_model=list[Fornecedor])
def list_suppliers() -> list[Fornecedor]:
    return fornecedores_service.list()

@router.post("", response_model=Fornecedor, status_code=status.HTTP_201_CREATED)
def create_supplier(data: FornecedorInput) -> Fornecedor:
    return fornecedores_service.create(data)

@router.put("/{item_id}", response_model=Fornecedor)
def update_supplier(item_id: str, data: FornecedorInput) -> Fornecedor:
    return fornecedores_service.update(item_id, data)

@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_supplier(item_id: str) -> None:
    fornecedores_service.delete(item_id)
