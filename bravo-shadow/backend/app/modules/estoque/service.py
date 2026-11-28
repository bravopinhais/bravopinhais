from collections.abc import Callable
from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException

from app.core.audit import AuditEvent
from app.core.authorization import AuthenticatedPrincipal
from app.core.repositories import CollectionRepository, InMemoryCollectionRepository
from .schemas import EstoqueInput, EstoqueItem


class EstoqueService:
    """Regras de estoque desacopladas do armazenamento."""

    def __init__(
        self,
        repository: CollectionRepository[EstoqueItem, str] | None = None,
        has_movement_references: Callable[[str], bool] | None = None,
        audit_sink=None,
    ) -> None:
        self.repository = repository if repository is not None else InMemoryCollectionRepository()
        self.audit_sink = audit_sink
        self._items = getattr(self.repository, "_items", {})
        self._has_movement_references = has_movement_references or (lambda _item_id: False)

    def set_movement_reference_checker(self, checker: Callable[[str], bool]) -> None:
        self._has_movement_references = checker

    def list(self) -> list[EstoqueItem]:
        return self.repository.list()

    def get(self, item_id: str) -> EstoqueItem:
        item = self.repository.get(item_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Produto não encontrado.")
        return item

    def create(self, data: EstoqueInput, *, actor: AuthenticatedPrincipal | None = None, request_id: str | None = None) -> EstoqueItem:
        self._require_actor_if_audited(actor)
        item = EstoqueItem(id=f"est_shadow_{uuid4().hex}", **data.model_dump())
        if self.audit_sink is not None:
            operation = getattr(self.repository, "add_audited", None)
            self._require_audited_operation(operation)
            operation(item.id, item, self._event(actor, "estoque:create", item.id, request_id), self.audit_sink)
        else:
            self.repository.add(item.id, item)
        return item

    def update(self, item_id: str, data: EstoqueInput, *, actor: AuthenticatedPrincipal | None = None, request_id: str | None = None) -> EstoqueItem:
        self._require_actor_if_audited(actor)
        current = self.get(item_id)
        if self._has_movement_references(item_id) and data.quantidade != current.quantidade:
            raise HTTPException(
                status_code=409,
                detail=(
                    "O saldo deste produto possui histórico de movimentações. "
                    "Altere a quantidade por um acerto de estoque."
                ),
            )
        item = EstoqueItem(id=item_id, **data.model_dump())
        if self.audit_sink is not None:
            operation = getattr(self.repository, "replace_audited", None)
            self._require_audited_operation(operation)
            operation(item_id, item, self._event(actor, "estoque:update", item_id, request_id), self.audit_sink)
        else:
            self.repository.replace(item_id, item)
        return item

    def update_quantity(self, item_id: str, quantity: Decimal, *, actor: AuthenticatedPrincipal | None = None, request_id: str | None = None) -> EstoqueItem:
        self._require_actor_if_audited(actor)
        product = self.get(item_id)
        updated = product.model_copy(update={"quantidade": quantity})
        if self.audit_sink is not None:
            operation = getattr(self.repository, "replace_audited", None)
            self._require_audited_operation(operation)
            operation(item_id, updated, self._event(actor, "estoque:quantity_update", item_id, request_id), self.audit_sink)
        else:
            self.repository.replace(item_id, updated)
        return updated

    def delete(self, item_id: str, *, actor: AuthenticatedPrincipal | None = None, request_id: str | None = None) -> None:
        self._require_actor_if_audited(actor)
        self.get(item_id)
        if self._has_movement_references(item_id):
            raise HTTPException(
                status_code=409,
                detail="O produto possui movimentações e não pode ser excluído.",
            )
        if self.audit_sink is not None:
            operation = getattr(self.repository, "delete_audited", None)
            self._require_audited_operation(operation)
            operation(item_id, self._event(actor, "estoque:delete", item_id, request_id), self.audit_sink)
        else:
            self.repository.delete(item_id)

    def _require_actor_if_audited(self, actor: AuthenticatedPrincipal | None) -> None:
        if self.audit_sink is not None and (
            not isinstance(actor, AuthenticatedPrincipal)
            or actor.account_status != "Ativo"
            or not isinstance(actor.subject, str)
            or not actor.subject.strip()
        ):
            raise HTTPException(status_code=403, detail="Identidade autenticada obrigatória para operações auditadas do Estoque.")

    @staticmethod
    def _event(actor: AuthenticatedPrincipal | None, action: str, item_id: str, request_id: str | None) -> AuditEvent:
        if not isinstance(actor, AuthenticatedPrincipal):
            raise HTTPException(status_code=403, detail="Ator de auditoria inválido.")
        return AuditEvent(
            actor_subject=actor.subject.strip(), action=action,
            entity_type="estoque", entity_id=item_id,
            outcome="success", request_id=request_id,
        )

    @staticmethod
    def _require_audited_operation(operation) -> None:
        if not callable(operation):
            raise HTTPException(status_code=503, detail="Persistência e auditoria transacional indisponíveis.")

# Compatibilidade temporária para consumidores legados fora dos routers.
# A aplicação FastAPI usa instâncias isoladas criadas em build_storage_services().
estoque_service = EstoqueService()
