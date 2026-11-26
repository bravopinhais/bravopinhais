from collections.abc import Callable
from uuid import uuid4

from fastapi import HTTPException, status

from app.core.repositories import CollectionRepository, InMemoryCollectionRepository
from .schemas import PlanoConta, PlanoContaInput


class PlanoContasService:
    """Regras de Plano de Contas desacopladas do mecanismo de persistência."""

    def __init__(
        self,
        repository: CollectionRepository[PlanoConta, str] | None = None,
        has_financial_references: Callable[[str], bool] | None = None,
    ) -> None:
        self.repository = repository or InMemoryCollectionRepository()
        self._items = getattr(self.repository, "_items", {})
        self._has_financial_references = has_financial_references

    def list(self) -> list[PlanoConta]:
        return sorted(self.repository.list(), key=lambda item: item.codigo)

    def create(self, data: PlanoContaInput) -> PlanoConta:
        self._ensure_unique_code(data.codigo)
        item = PlanoConta(id=f"pc_shadow_{uuid4().hex}", **data.model_dump())
        self.repository.add(item.id, item)
        return item

    def update(self, item_id: str, data: PlanoContaInput, expected_version: int) -> PlanoConta:
        # A operação CAS do repositório é a autoridade para existência e versão.
        # No PostgreSQL, isso evita uma leitura extra e fecha a janela entre GET e UPDATE.
        self._ensure_unique_code(data.codigo, excluding=item_id)
        item = PlanoConta(id=item_id, version=expected_version, **data.model_dump())
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

    def delete(self, item_id: str) -> None:
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
        self.repository.delete(item_id)

    def _ensure_unique_code(self, codigo: str, excluding: str | None = None) -> None:
        normalized = codigo.casefold()
        if any(item.id != excluding and item.codigo.casefold() == normalized for item in self.repository.list()):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Já existe uma conta com este código.")


plano_contas_service = PlanoContasService()
