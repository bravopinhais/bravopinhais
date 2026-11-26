from uuid import uuid4
from fastapi import HTTPException, status
from .schemas import Empregado, EmpregadoInput

class EmpregadosService:
    def __init__(self) -> None:
        self._items: dict[str, Empregado] = {}
    def list(self) -> list[Empregado]:
        return list(self._items.values())
    def create(self, data: EmpregadoInput) -> Empregado:
        item = Empregado(id=f"emp_shadow_{uuid4().hex}", **data.model_dump())
        self._items[item.id] = item
        return item
    def update(self, item_id: str, data: EmpregadoInput) -> Empregado:
        if item_id not in self._items:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empregado não encontrado.")
        item = Empregado(id=item_id, **data.model_dump())
        self._items[item_id] = item
        return item
    def delete(self, item_id: str) -> None:
        if item_id not in self._items:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empregado não encontrado.")
        del self._items[item_id]

empregados_service = EmpregadosService()
