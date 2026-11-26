from uuid import uuid4

from fastapi import HTTPException, status

from app.core.repositories import CollectionRepository, InMemoryCollectionRepository
from .schemas import Empregado, EmpregadoInput


class EmpregadosService:
    def __init__(
        self,
        repository: CollectionRepository[Empregado, str] | None = None,
    ) -> None:
        self.repository = repository if repository is not None else InMemoryCollectionRepository()
        self._items = getattr(self.repository, "_items", {})

    def list(self) -> list[Empregado]:
        return self.repository.list()

    def create(self, data: EmpregadoInput) -> Empregado:
        item = Empregado(id=f"emp_shadow_{uuid4().hex}", **data.model_dump())
        self.repository.add(item.id, item)
        return item

    def update(self, item_id: str, data: EmpregadoInput) -> Empregado:
        if not self.repository.exists(item_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empregado não encontrado.")
        item = Empregado(id=item_id, **data.model_dump())
        self.repository.replace(item_id, item)
        return item

    def delete(self, item_id: str) -> None:
        if not self.repository.exists(item_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empregado não encontrado.")
        self.repository.delete(item_id)


empregados_service = EmpregadosService()
