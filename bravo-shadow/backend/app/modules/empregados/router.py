from fastapi import APIRouter, status
from .schemas import Empregado, EmpregadoInput
from .service import empregados_service

router = APIRouter(prefix="/api/v1/empregados", tags=["Empregados"])

@router.get("", response_model=list[Empregado])
def list_employees() -> list[Empregado]:
    return empregados_service.list()

@router.post("", response_model=Empregado, status_code=status.HTTP_201_CREATED)
def create_employee(data: EmpregadoInput) -> Empregado:
    return empregados_service.create(data)

@router.put("/{item_id}", response_model=Empregado)
def update_employee(item_id: str, data: EmpregadoInput) -> Empregado:
    return empregados_service.update(item_id, data)

@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(item_id: str) -> None:
    empregados_service.delete(item_id)
