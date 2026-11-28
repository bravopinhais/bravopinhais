from datetime import datetime
from uuid import uuid4

from fastapi import HTTPException

from app.core.audit import AuditEvent
from app.core.authorization import AuthenticatedPrincipal
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
        audit_sink=None,
    ) -> None:
        self.repository = repository if repository is not None else InMemoryCollectionRepository()
        self._items = getattr(self.repository, "_items", {})
        self.inventory_service = (
            inventory_service if inventory_service is not None else estoque_service
        )
        self.reason_service = reason_service
        self.movement_repository = movement_repository
        self.audit_sink = audit_sink

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

    def create(self, data: AcertoInput, *, actor: AuthenticatedPrincipal | None = None, request_id: str | None = None) -> Acerto:
        if self.audit_sink is not None and (
            not isinstance(actor, AuthenticatedPrincipal)
            or actor.account_status != "Ativo"
            or not isinstance(actor.subject, str)
            or not actor.subject.strip()
        ):
            raise HTTPException(status_code=403, detail="Identidade autenticada obrigatória para acertos de estoque auditados.")
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
            if self.audit_sink is not None:
                operation = getattr(self.movement_repository, "register_movement_audited", None)
                if not callable(operation) or not callable(getattr(self.audit_sink, "append_in_transaction", None)):
                    raise HTTPException(status_code=503, detail="Persistência e auditoria transacional indisponíveis.")
                event = AuditEvent(
                    actor_subject=actor.subject.strip(),
                    action="acertos_estoque:create",
                    entity_type="acerto_estoque",
                    entity_id=item.id,
                    outcome="success",
                    request_id=request_id,
                )
                return operation(
                    product_id=product.id,
                    movement=item,
                    delta=data.quantidade if data.tipo == "Entrada" else -data.quantidade,
                    event=event,
                    audit_sink=self.audit_sink,
                )
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
