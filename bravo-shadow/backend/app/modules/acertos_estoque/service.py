from datetime import datetime
from uuid import uuid4

from fastapi import HTTPException

from app.core.repositories import CollectionRepository, InMemoryCollectionRepository
from app.modules.estoque.service import EstoqueService, estoque_service
from app.modules.motivos_acerto.service import MotivosAcertoService
from .schemas import Acerto, AcertoInput


class AcertosEstoqueService:
    """Registra movimentos associados a uma instância específica do estoque."""

    def __init__(
        self,
        repository: CollectionRepository[Acerto, str] | None = None,
        inventory_service: EstoqueService | None = None,
        reason_service: MotivosAcertoService | None = None,
        movement_repository=None,
    ) -> None:
        self.repository = repository if repository is not None else InMemoryCollectionRepository()
        self._items = getattr(self.repository, "_items", {})
        self.inventory_service = (
            inventory_service if inventory_service is not None else estoque_service
        )
        self.reason_service = reason_service
        self.movement_repository = movement_repository

    def list(self) -> list[Acerto]:
        return self.repository.list()

    def has_product_reference(self, product_id: str) -> bool:
        checker = getattr(self.repository, "any", None)
        if callable(checker):
            return checker(lambda item: item.produtoId == product_id)
        return any(item.produtoId == product_id for item in self.repository.list())

    def has_reason_reference(self, reason_id: str) -> bool:
        checker = getattr(self.repository, "any", None)
        if callable(checker):
            return checker(lambda item: item.motivoId == reason_id)
        return any(item.motivoId == reason_id for item in self.repository.list())

    def create(self, data: AcertoInput) -> Acerto:
        product = self.inventory_service.get(data.produtoId)
        reason_name = data.motivo
        if data.motivoId:
            if self.reason_service is None:
                raise HTTPException(status_code=400, detail="Vínculo de motivo não está configurado.")
            reason_name = self.reason_service.get(data.motivoId).nome

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
        values = data.model_dump()
        values["motivo"] = reason_name
        item = Acerto(
            id=f"ac_shadow_{uuid4().hex}",
            data=datetime.now().astimezone().isoformat(),
            **values,
        )
        if self.movement_repository is not None:
            # O adaptador persistente relê o saldo com FOR UPDATE e grava
            # saldo + histórico em uma única transação PostgreSQL.
            return self.movement_repository.register_movement(
                product_id=product.id,
                movement=item,
                delta=data.quantidade if data.tipo == "Entrada" else -data.quantidade,
            )

        # O adaptador em memória preserva o comportamento atual para testes.
        self.inventory_service.update_quantity(product.id, new_quantity)
        self.repository.add(item.id, item)
        return item

    def delete(self, item_id: str) -> None:
        if not self.repository.exists(item_id):
            raise HTTPException(status_code=404, detail="Acerto não encontrado.")
        raise HTTPException(
            status_code=409,
            detail=(
                "Movimentações de estoque são imutáveis para preservar o saldo e o histórico. "
                "A correção deve ser feita por um movimento compensatório."
            ),
        )


acertos_estoque_service = AcertosEstoqueService()
