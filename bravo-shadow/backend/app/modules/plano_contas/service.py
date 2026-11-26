from uuid import uuid4

from fastapi import HTTPException, status

from .schemas import PlanoConta, PlanoContaInput


class PlanoContasService:
    """Armazenamento temporário em memória para homologação, sem banco conectado."""

    def __init__(self) -> None:
        self._items: dict[str, PlanoConta] = {}

    def list(self) -> list[PlanoConta]:
        return sorted(self._items.values(), key=lambda item: item.codigo)

    def create(self, data: PlanoContaInput) -> PlanoConta:
        self._ensure_unique_code(data.codigo)
        item = PlanoConta(id=f"pc_shadow_{uuid4().hex}", **data.model_dump())
        self._items[item.id] = item
        return item

    def update(self, item_id: str, data: PlanoContaInput) -> PlanoConta:
        if item_id not in self._items:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conta não encontrada.")
        self._ensure_unique_code(data.codigo, excluding=item_id)
        item = PlanoConta(id=item_id, **data.model_dump())
        self._items[item_id] = item
        return item

    def delete(self, item_id: str) -> None:
        if item_id not in self._items:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conta não encontrada.")
        del self._items[item_id]

    def _ensure_unique_code(self, codigo: str, excluding: str | None = None) -> None:
        normalized = codigo.casefold()
        if any(
            item.id != excluding and item.codigo.casefold() == normalized
            for item in self._items.values()
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Já existe uma conta com este código.",
            )


plano_contas_service = PlanoContasService()
