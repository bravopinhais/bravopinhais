from collections.abc import Callable
from uuid import uuid4

from fastapi import HTTPException, status

from app.core.audit import AuditEvent
from app.core.authorization import AuthenticatedPrincipal
from app.core.repositories import CollectionRepository, InMemoryCollectionRepository
from .schemas import PlanoConta, PlanoContaInput


class PlanoContasService:
    """Regras de Plano de Contas; mutações HTTP exigem auditoria transacional."""

    def __init__(
        self,
        repository: CollectionRepository[PlanoConta, str] | None = None,
        has_financial_references: Callable[[str], bool] | None = None,
        audit_sink=None,
    ) -> None:
        self.repository = repository or InMemoryCollectionRepository()
        self._items = getattr(self.repository, "_items", {})
        self._has_financial_references = has_financial_references
        self.audit_sink = audit_sink

    def list(self) -> list[PlanoConta]:
        return sorted(self.repository.list(), key=lambda item: item.codigo)

    def create(
        self, data: PlanoContaInput, *, actor: AuthenticatedPrincipal | None = None,
        request_id: str | None = None,
    ) -> PlanoConta:
        self._ensure_unique_code(data.codigo)
        item = PlanoConta(id=f"pc_shadow_{uuid4().hex}", **data.model_dump())
        if actor is None:
            self.repository.add(item.id, item)
            return item
        event = self._audit_event(actor, "plano_contas:create", item.id, request_id)
        operation = getattr(self.repository, "add_audited", None)
        self._require_audited(operation)
        operation(item, event, self.audit_sink)
        return item

    def update(
        self, item_id: str, data: PlanoContaInput, expected_version: int, *,
        actor: AuthenticatedPrincipal | None = None, request_id: str | None = None,
    ) -> PlanoConta:
        self._ensure_unique_code(data.codigo, excluding=item_id)
        item = PlanoConta(id=item_id, version=expected_version, **data.model_dump())
        if actor is not None:
            event = self._audit_event(actor, "plano_contas:update", item_id, request_id)
            operation = getattr(self.repository, "replace_if_version_audited", None)
            self._require_audited(operation)
            result = operation(item, expected_version, event, self.audit_sink)
            return item.model_copy(update={"version": result})

        # Compatibilidade para chamadas internas existentes; as rotas HTTP
        # sempre fornecem actor e usam exclusivamente a operação auditada.
        compare_and_swap = getattr(self.repository, "replace_if_version", None)
        if compare_and_swap is None:
            raise HTTPException(status_code=503, detail="Repositório sem suporte a controle de versão.")
        result = compare_and_swap(item_id, item, expected_version)
        if result == 0:
            raise HTTPException(status_code=404, detail="Conta não encontrada.")
        if result == -1:
            raise HTTPException(status_code=409, detail="A conta foi alterada por outra operação. Recarregue os dados.")
        if isinstance(result, int):
            return item.model_copy(update={"version": result})
        return item

    def delete(
        self, item_id: str, *, actor: AuthenticatedPrincipal | None = None,
        request_id: str | None = None,
    ) -> None:
        if not self.repository.exists(item_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conta não encontrada.")
        if self._has_financial_references is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Exclusão temporariamente indisponível: verificação de vínculos financeiros ainda não configurada.",
            )
        if self._has_financial_references(item_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Esta conta possui lançamentos financeiros vinculados e não pode ser excluída.",
            )
        if actor is not None:
            event = self._audit_event(actor, "plano_contas:delete", item_id, request_id)
            operation = getattr(self.repository, "delete_audited", None)
            self._require_audited(operation)
            operation(item_id, event, self.audit_sink)
            return
        self.repository.delete(item_id)

    @staticmethod
    def _audit_event(
        actor: AuthenticatedPrincipal, action: str, entity_id: str,
        request_id: str | None,
    ) -> AuditEvent:
        if (
            not isinstance(actor, AuthenticatedPrincipal)
            or actor.account_status != "Ativo"
            or not actor.subject.strip()
        ):
            raise HTTPException(status_code=403, detail="Ator administrativo inválido.")
        return AuditEvent(
            actor_subject=actor.subject.strip(),
            action=action,
            entity_type="plano_conta",
            entity_id=entity_id,
            outcome="success",
            request_id=request_id,
        )

    def _require_audited(self, operation) -> None:
        if not callable(operation) or not callable(getattr(self.audit_sink, "append_in_transaction", None)):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Persistência e auditoria transacional indisponíveis. Nenhuma alteração foi confirmada.",
            )

    def _ensure_unique_code(self, codigo: str, excluding: str | None = None) -> None:
        normalized = codigo.casefold()
        if any(item.id != excluding and item.codigo.casefold() == normalized for item in self.repository.list()):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Já existe uma conta com este código.")


plano_contas_service = PlanoContasService()
