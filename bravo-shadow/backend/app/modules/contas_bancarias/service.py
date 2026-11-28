from uuid import uuid4

from fastapi import HTTPException, status

from app.core.repositories import CollectionRepository, InMemoryCollectionRepository
from .schemas import ContaBancaria, ContaBancariaInput


class ContasBancariasService:
    """Cadastro de banco e saldo informado; não é conciliação bancária."""

    def __init__(
        self,
        repository: CollectionRepository[ContaBancaria, str] | None = None,
        audit_sink=None,
    ) -> None:
        self.repository = repository if repository is not None else InMemoryCollectionRepository()
        self.audit_sink = audit_sink
        self._items = getattr(self.repository, "_items", {})

    def list(self) -> list[ContaBancaria]:
        return self.repository.list()

    def create(self, data: ContaBancariaInput) -> ContaBancaria:
        self._ensure_mutation_audit_ready()
        item = ContaBancaria(id=f"cb_shadow_{uuid4().hex}", **data.model_dump())
        self.repository.add(item.id, item)
        return item

    def update(self, item_id: str, data: ContaBancariaInput) -> ContaBancaria:
        self._ensure_mutation_audit_ready()
        if not self.repository.exists(item_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conta bancária não encontrada.")
        item = ContaBancaria(id=item_id, **data.model_dump())
        self.repository.replace(item_id, item)
        return item

    def delete(self, item_id: str) -> None:
        self._ensure_mutation_audit_ready()
        if not self.repository.exists(item_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conta bancária não encontrada.")
        self.repository.delete(item_id)

    def _ensure_mutation_audit_ready(self) -> None:
        if self.audit_sink is not None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Mutações de contas bancárias bloqueadas até a auditoria transacional ser integrada.",
            )


contas_bancarias_service = ContasBancariasService()
