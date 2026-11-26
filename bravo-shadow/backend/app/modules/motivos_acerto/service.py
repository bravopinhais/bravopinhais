from collections.abc import Callable
from uuid import uuid4

from fastapi import HTTPException

from app.core.repositories import CollectionRepository, InMemoryCollectionRepository
from .schemas import MotivoAcerto, MotivoAcertoInput


class MotivosAcertoService:
    def __init__(
        self,
        repository: CollectionRepository[MotivoAcerto, str] | None = None,
        has_adjustment_references: Callable[[str], bool] | None = None,
    ) -> None:
        self.repository = repository if repository is not None else InMemoryCollectionRepository()
        self._items = getattr(self.repository, "_items", {})
        self._has_adjustment_references = has_adjustment_references or (lambda _item_id: False)

    def set_reference_checker(self, checker: Callable[[str], bool]) -> None:
        self._has_adjustment_references = checker

    def list(self) -> list[MotivoAcerto]:
        return self.repository.list()

    def get(self, item_id: str) -> MotivoAcerto:
        item = self.repository.get(item_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Motivo não encontrado.")
        return item

    def create(self, data: MotivoAcertoInput) -> MotivoAcerto:
        item = MotivoAcerto(id=f"mot_shadow_{uuid4().hex}", nome=data.nome)
        self.repository.add(item.id, item)
        return item

    def delete(self, item_id: str) -> None:
        self.get(item_id)
        if self._has_adjustment_references(item_id):
            raise HTTPException(
                status_code=409,
                detail="Não é possível excluir um motivo utilizado em acertos de estoque.",
            )
        self.repository.delete(item_id)


motivos_acerto_service = MotivosAcertoService()
