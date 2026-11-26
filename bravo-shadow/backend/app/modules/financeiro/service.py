from uuid import uuid4

from fastapi import HTTPException, status

from .schemas import FinanceiroInput, FinanceiroTitulo


class FinanceiroService:
    """Repositório temporário em memória; não conectado ao banco de produção."""

    def __init__(self) -> None:
        self._items: dict[str, FinanceiroTitulo] = {}

    def list(self) -> list[FinanceiroTitulo]:
        return list(self._items.values())

    def create(self, data: FinanceiroInput) -> FinanceiroTitulo:
        item = FinanceiroTitulo(id=f"fin_shadow_{uuid4().hex}", **data.model_dump())
        self._items[item.id] = item
        return item

    def update(self, item_id: str, data: FinanceiroInput) -> FinanceiroTitulo:
        if item_id not in self._items:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Título não encontrado.")
        item = FinanceiroTitulo(id=item_id, **data.model_dump())
        self._items[item_id] = item
        return item

    def delete(self, item_id: str) -> None:
        if item_id not in self._items:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Título não encontrado.")
        del self._items[item_id]

    def has_plan_account_reference(self, account_id: str) -> bool:
        return any(item.planoContaId == account_id for item in self._items.values())


financeiro_service = FinanceiroService()
