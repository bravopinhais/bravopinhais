from uuid import uuid4

from fastapi import HTTPException, status

from app.core.audit import AuditEvent
from app.core.authorization import AuthenticatedPrincipal

from app.core.repositories import CollectionRepository, InMemoryCollectionRepository
from .schemas import FinanceiroInput, FinanceiroTitulo


class FinanceiroService:
    """Regras financeiras independentes do mecanismo de persistência."""

    def __init__(self, repository: CollectionRepository[FinanceiroTitulo, str] | None = None, audit_sink=None) -> None:
        self.repository = repository or InMemoryCollectionRepository()
        self.audit_sink = audit_sink
        self._items = getattr(self.repository, "_items", {})

    def list(self) -> list[FinanceiroTitulo]:
        return self.repository.list()

    def create(self, data: FinanceiroInput, *, actor: AuthenticatedPrincipal | None = None, request_id: str | None = None) -> FinanceiroTitulo:
        item = FinanceiroTitulo(id=f"fin_shadow_{uuid4().hex}", **data.model_dump())
        if actor is None:
            self.repository.add(item.id, item)
            return item
        event = self._audit_event(actor, "financeiro:create", item.id, request_id)
        operation = getattr(self.repository, "add_audited", None)
        self._require_audited(operation)
        operation(item, event, self.audit_sink)
        return item

    def update(self, item_id: str, data: FinanceiroInput, expected_version: int, *, actor: AuthenticatedPrincipal | None = None, request_id: str | None = None) -> FinanceiroTitulo:
        # A operação CAS do repositório distingue registro ausente de versão obsoleta.
        # Não é necessário fazer uma leitura separada antes do UPDATE.
        item = FinanceiroTitulo(id=item_id, version=expected_version, **data.model_dump())
        if actor is not None:
            event = self._audit_event(actor, "financeiro:update", item_id, request_id)
            operation = getattr(self.repository, "replace_if_version_audited", None)
            self._require_audited(operation)
            result = operation(item, expected_version, event, self.audit_sink)
            return item.model_copy(update={"version": result})
        compare_and_swap = getattr(self.repository, "replace_if_version", None)
        if compare_and_swap is None:
            raise HTTPException(status_code=503, detail="Repositório sem suporte a controle de versão.")
        result = compare_and_swap(item_id, item, expected_version)
        if result == 0:
            raise HTTPException(status_code=404, detail="Título não encontrado.")
        if result == -1:
            raise HTTPException(status_code=409, detail="O título foi alterado por outra operação. Recarregue os dados.")
        if isinstance(result, int):
            return item.model_copy(update={"version": result})
        return item

    def delete(self, item_id: str, *, actor: AuthenticatedPrincipal | None = None, request_id: str | None = None) -> None:
        if not self.repository.exists(item_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Título não encontrado.")
        if actor is not None:
            event = self._audit_event(actor, "financeiro:delete", item_id, request_id)
            operation = getattr(self.repository, "delete_audited", None)
            self._require_audited(operation)
            operation(item_id, event, self.audit_sink)
            return
        self.repository.delete(item_id)

    @staticmethod
    def _audit_event(actor, action: str, entity_id: str, request_id: str | None) -> AuditEvent:
        if not isinstance(actor, AuthenticatedPrincipal) or actor.account_status != "Ativo" or not actor.subject.strip():
            raise HTTPException(status_code=403, detail="Ator administrativo inválido.")
        return AuditEvent(actor_subject=actor.subject.strip(), action=action, entity_type="financeiro", entity_id=entity_id, outcome="success", request_id=request_id)

    def _require_audited(self, operation) -> None:
        if not callable(operation) or not callable(getattr(self.audit_sink, "append_in_transaction", None)):
            raise HTTPException(status_code=503, detail="Persistência e auditoria transacional indisponíveis. Nenhuma alteração foi confirmada.")

    def has_plan_account_reference(self, account_id: str) -> bool:
        # Prefere a consulta EXISTS do adapter PostgreSQL, evitando carregar
        # todos os títulos financeiros apenas para verificar um vínculo.
        checker = getattr(self.repository, "has_plan_account_reference", None)
        if callable(checker):
            return checker(account_id)

        # O adapter em memória oferece busca protegida pelo seu próprio lock.
        any_match = getattr(self.repository, "any", None)
        if callable(any_match):
            return any_match(lambda item: item.planoContaId == account_id)

        # Compatibilidade com adapters simples que implementem apenas list().
        return any(item.planoContaId == account_id for item in self.repository.list())


financeiro_service = FinanceiroService()
