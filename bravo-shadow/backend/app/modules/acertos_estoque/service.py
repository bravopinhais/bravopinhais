from datetime import datetime
from uuid import uuid4

from fastapi import HTTPException

from app.core.repositories import CollectionRepository, InMemoryCollectionRepository
from app.modules.estoque.service import EstoqueService, estoque_service
from .schemas import Acerto, AcertoInput


class AcertosEstoqueService:
    """Registra movimentos associados a uma instância específica do estoque."""

    def __init__(
        self,
        repository: CollectionRepository[Acerto, str] | None = None,
        inventory_service: EstoqueService | None = None,
    ) -> None:
        self.repository = repository if repository is not None else InMemoryCollectionRepository()
        self._items = getattr(self.repository, "_items", {})
        self.inventory_service = (
            inventory_service if inventory_service is not None else estoque_service
        )

    def list(self) -> list[Acerto]:
        return self.repository.list()

    def create(self, data: AcertoInput) -> Acerto:
        product = self.inventory_service.get(data.produtoId)
        current = product.quantidade
        if data.tipo == "Saída" and data.quantidade > current:
            raise HTTPException(
                status_code=409,
                detail="Quantidade de saída superior ao saldo disponível.",
            )
        new_quantity = (
            current + data.quantidade
            if data.tipo == "Entrada"
            else current - data.quantidade
        )
        item = Acerto(
            id=f"ac_shadow_{uuid4().hex}",
            data=datetime.now().astimezone().isoformat(),
            **data.model_dump(),
        )
        # Memória não oferece transação ACID. O futuro adaptador PostgreSQL
        # deverá atualizar saldo e histórico na mesma transação.
        self.inventory_service.update_quantity(product.id, new_quantity)
        self.repository.add(item.id, item)
        return item

    def delete(self, item_id: str) -> None:
        if not self.repository.exists(item_id):
            raise HTTPException(status_code=404, detail="Acerto não encontrado.")
        # Não reverte o saldo: comportamento legado preservado nesta etapa.
        self.repository.delete(item_id)


# Compatibilidade temporária para consumidores legados fora dos routers.
acertos_estoque_service = AcertosEstoqueService()
