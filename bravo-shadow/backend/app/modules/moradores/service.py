from uuid import uuid4
from fastapi import HTTPException, status
from .schemas import Morador, MoradorInput, MoradorImportBatch

class MoradoresService:
    def __init__(self) -> None:
        self._items: dict[str, Morador] = {}
    def list(self, bloco: str | None = None, busca: str | None = None) -> list[Morador]:
        items = list(self._items.values())
        if bloco:
            items = [item for item in items if item.bloco.strip() == bloco.strip()]
        if busca:
            term = busca.casefold().strip()
            items = [item for item in items if term in item.nome.casefold() or term in item.apartamento.casefold()]
        return items
    def create(self, data: MoradorInput) -> Morador:
        item = Morador(id=f"mor_shadow_{uuid4().hex}", **data.model_dump())
        self._items[item.id] = item
        return item
    def update(self, item_id: str, data: MoradorInput) -> Morador:
        if item_id not in self._items:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Morador não encontrado.")
        item = Morador(id=item_id, **data.model_dump())
        self._items[item_id] = item
        return item
    def delete(self, item_id: str) -> None:
        if item_id not in self._items:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Morador não encontrado.")
        del self._items[item_id]
    def import_batch(self, batch: MoradorImportBatch) -> int:
        for data in batch.moradores:
            item = Morador(id=f"mor_import_{uuid4().hex}", **data.model_dump())
            self._items[item.id] = item
        return len(batch.moradores)

moradores_service = MoradoresService()
