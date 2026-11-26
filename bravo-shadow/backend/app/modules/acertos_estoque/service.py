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
    ) -> None:
        self.repository = repository if repository is not None else InMemoryCollectionRepository()
        self._items = getattr(self.repository, "_items", {})
        self.inventory_service = (
            inventory_service if inventory_service is not None else estoque_service
        )
        self.reason_service = reason_service

    def list(self) -> list[Acerto]:
        return self.repository.list()

    def has_reason_reference(self, reason_id: str) -> bool:
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


acertos_estoque_service = AcertosEstoqueService()
