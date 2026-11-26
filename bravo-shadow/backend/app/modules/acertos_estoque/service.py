from datetime import datetime
from uuid import uuid4

from fastapi import HTTPException

from app.core.repositories import CollectionRepository, InMemoryCollectionRepository
from app.modules.estoque.service import estoque_service
from .schemas import Acerto, AcertoInput


class AcertosEstoqueService:
    """Registra movimentos usando serviços/repositórios, sem acessar estado alheio."""

    def __init__(
        self,
        repository: CollectionRepository[Acerto, str] | None = None,
        inventory_service=None,
    ) -> None:
        self.repository = repository or InMemoryCollectionRepository()
        self._items = getattr(self.repository, "_items", {})
        self.inventory_service = inventory_service or estoque_service

    def list(self) -> list[Acerto]:
        return self.repository.list()

    def create(self, data: AcertoInput) -> Acerto:
        product = self.inventory_service.get(data.produtoId)
        current = product.quantidade
        if data.tipo == "Saída" and data.quantidade > current:
            raise HTTPException(status_code=409, detail="Quantidade de saída superior ao saldo disponível.")
        new_quantity = current + data.quantidade if data.tipo == "Entrada" else current - data.quantidade
        item = Acerto(
            id=f"ac_shadow_{uuid4().hex}",
            data=datetime.now().astimezone().isoformat(),
            **data.model_dump(),
        )
        # O adaptador em memória não oferece transação ACID. A implementação
        # PostgreSQL deverá mover saldo e histórico na mesma transação.
        self.inventory_service.update_quantity(product.id, new_quantity)
        self.repository.add(item.id, item)
        return item

    def delete(self, item_id: str) -> None:
        if not self.repository.exists(item_id):
            raise HTTPException(status_code=404, detail="Acerto não encontrado.")
        # Regra legada mantida na sombra; persistência bloqueará exclusão destrutiva.
        self.repository.delete(item_id)


acertos_estoque_service = AcertosEstoqueService()
