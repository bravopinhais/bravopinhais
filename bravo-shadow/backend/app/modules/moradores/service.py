from uuid import uuid4

from app.core.authorization import AuthenticatedPrincipal

from fastapi import HTTPException, status

from app.core.repositories import CollectionRepository, InMemoryCollectionRepository
from .schemas import Morador, MoradorInput, MoradorImportBatch


class MoradoresService:
    def __init__(
        self,
        repository: CollectionRepository[Morador, str] | None = None,
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

    def list(self, bloco: str | None = None, busca: str | None = None) -> list[Morador]:
        items = self.repository.list()
        if bloco:
            items = [item for item in items if item.bloco.strip() == bloco.strip()]
        if busca:
            term = busca.casefold().strip()
            items = [
                item for item in items
                if term in item.nome.casefold() or term in item.apartamento.casefold()
            ]
        return items

    def get(self, item_id: str) -> Morador:
        item = self.repository.get(item_id)
        if item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Morador não encontrado.")
        return item

    def create(self, data: MoradorInput, *, actor: AuthenticatedPrincipal | None = None, request_id: str | None = None) -> Morador:
        self._require_audited_write(actor)
        item = Morador(id=f"mor_shadow_{uuid4().hex}", **data.model_dump())
        self.repository.add(item.id, item)
        return item

    def update(self, item_id: str, data: MoradorInput, *, actor: AuthenticatedPrincipal | None = None, request_id: str | None = None) -> Morador:
        self._require_audited_write(actor)
        if not self.repository.exists(item_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Morador não encontrado.")
        item = Morador(id=item_id, **data.model_dump())
        self.repository.replace(item_id, item)
        return item

    def delete(self, item_id: str, *, actor: AuthenticatedPrincipal | None = None, request_id: str | None = None) -> None:
        self._require_audited_write(actor)
        if not self.repository.exists(item_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Morador não encontrado.")
        self.repository.delete(item_id)

    def import_batch(self, batch: MoradorImportBatch, *, actor: AuthenticatedPrincipal | None = None, request_id: str | None = None) -> int:
        self._require_audited_write(actor)
        for data in batch.moradores:
            item = Morador(id=f"mor_import_{uuid4().hex}", **data.model_dump())
            self.repository.add(item.id, item)
        return len(batch.moradores)


moradores_service = MoradoresService()
