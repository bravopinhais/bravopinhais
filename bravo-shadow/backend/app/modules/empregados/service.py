from uuid import uuid4

from app.core.authorization import AuthenticatedPrincipal

from fastapi import HTTPException, status

from app.core.repositories import CollectionRepository, InMemoryCollectionRepository
from .schemas import Empregado, EmpregadoInput


class EmpregadosService:
    def __init__(
        self,
        repository: CollectionRepository[Empregado, str] | None = None,
    ) -> None:
        self.repository = repository if repository is not None else InMemoryCollectionRepository()
        self._items = getattr(self.repository, "_items", {})
        self.audit_sink = None

    def _require_audited_write(self, actor: AuthenticatedPrincipal | None) -> None:
        if self.audit_sink is None:
            return
        if not isinstance(actor, AuthenticatedPrincipal) or actor.account_status != "Ativo" or not isinstance(actor.subject, str) or not actor.subject.strip():
            raise HTTPException(status_code=403, detail="Identidade interna ativa obrigatória para alterar este cadastro.")
        raise HTTPException(status_code=503, detail="Gravação auditada deste módulo ainda não foi homologada; alteração bloqueada para preservar a integridade.")

    def list(self) -> list[Empregado]:
        return self.repository.list()

    def create(self, data: EmpregadoInput, *, actor: AuthenticatedPrincipal | None = None, request_id: str | None = None) -> Empregado:
        self._require_audited_write(actor)
        item = Empregado(id=f"emp_shadow_{uuid4().hex}", **data.model_dump())
        self.repository.add(item.id, item)
        return item

    def update(self, item_id: str, data: EmpregadoInput, *, actor: AuthenticatedPrincipal | None = None, request_id: str | None = None) -> Empregado:
        self._require_audited_write(actor)
        if not self.repository.exists(item_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empregado não encontrado.")
        item = Empregado(id=item_id, **data.model_dump())
        self.repository.replace(item_id, item)
        return item

    def delete(self, item_id: str, *, actor: AuthenticatedPrincipal | None = None, request_id: str | None = None) -> None:
        self._require_audited_write(actor)
        if not self.repository.exists(item_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empregado não encontrado.")
        self.repository.delete(item_id)


empregados_service = EmpregadosService()
