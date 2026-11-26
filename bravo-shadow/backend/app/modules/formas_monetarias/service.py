from uuid import uuid4

from fastapi import HTTPException, status

from .schemas import FormaMonetaria, FormaMonetariaInput


class FormasMonetariasService:
    """Armazenamento temporário em memória, sem ligação com produção."""

    def __init__(self) -> None:
        self._items: dict[str, FormaMonetaria] = {}

    def list(self) -> list[FormaMonetaria]:
        return list(self._items.values())

    def create(self, data: FormaMonetariaInput) -> FormaMonetaria:
        item = FormaMonetaria(id=f"fm_shadow_{uuid4().hex}", **data.model_dump())
        self._items[item.id] = item
        return item

    def update(self, item_id: str, data: FormaMonetariaInput) -> FormaMonetaria:
        if item_id not in self._items:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Forma monetária não encontrada.")
        item = FormaMonetaria(id=item_id, **data.model_dump())
        self._items[item_id] = item
        return item

    def delete(self, item_id: str) -> None:
        if item_id not in self._items:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Forma monetária não encontrada.")
        del self._items[item_id]


formas_monetarias_service = FormasMonetariasService()
