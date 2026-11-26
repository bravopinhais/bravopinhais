from uuid import uuid4

from fastapi import HTTPException

from app.core.repositories import CollectionRepository, InMemoryCollectionRepository
from .schemas import MotivoAcerto, MotivoAcertoInput


class MotivosAcertoService:
    def __init__(
        self,
        repository: CollectionRepository[MotivoAcerto, str] | None = None,
    ) -> None:
        self.repository = repository if repository is not None else InMemoryCollectionRepository()
        self._items = getattr(self.repository, "_items", {})

    def list(self) -> list[MotivoAcerto]:
        return self.repository.list()

    def create(self, data: MotivoAcertoInput) -> MotivoAcerto:
        item = MotivoAcerto(id=f"mot_shadow_{uuid4().hex}", nome=data.nome)
        self.repository.add(item.id, item)
        return item

    def delete(self, item_id: str) -> None:
        if not self.repository.exists(item_id):
            raise HTTPException(status_code=404, detail="Motivo não encontrado.")
        self.repository.delete(item_id)


motivos_acerto_service = MotivosAcertoService()
