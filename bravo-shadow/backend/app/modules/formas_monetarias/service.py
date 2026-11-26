from uuid import uuid4

from fastapi import HTTPException, status

from app.core.repositories import CollectionRepository, InMemoryCollectionRepository
from .schemas import FormaMonetaria, FormaMonetariaInput


class FormasMonetariasService:
    """Regras de formas monetárias independentes do mecanismo de persistência."""

    def __init__(
        self,
        repository: CollectionRepository[FormaMonetaria, str] | None = None,
    ) -> None:
        self.repository = repository or InMemoryCollectionRepository()
        self._items = getattr(self.repository, "_items", {})

    def list(self) -> list[FormaMonetaria]:
        return self.repository.list()

    def create(self, data: FormaMonetariaInput) -> FormaMonetaria:
        item = FormaMonetaria(id=f"fm_shadow_{uuid4().hex}", **data.model_dump())
        self.repository.add(item.id, item)
        return item

    def update(self, item_id: str, data: FormaMonetariaInput) -> FormaMonetaria:
        if not self.repository.exists(item_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Forma monetária não encontrada.",
            )
        item = FormaMonetaria(id=item_id, **data.model_dump())
        self.repository.replace(item_id, item)
        return item

    def delete(self, item_id: str) -> None:
        if not self.repository.exists(item_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Forma monetária não encontrada.",
            )
        self.repository.delete(item_id)


formas_monetarias_service = FormasMonetariasService()
