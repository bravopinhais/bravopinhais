from uuid import uuid4

from fastapi import HTTPException, status

from app.core.repositories import CollectionRepository, InMemoryCollectionRepository
from .schemas import FinanceiroInput, FinanceiroTitulo


class FinanceiroService:
    """Regras financeiras independentes do mecanismo de persistência."""

    def __init__(self, repository: CollectionRepository[FinanceiroTitulo, str] | None = None) -> None:
        self.repository = repository or InMemoryCollectionRepository()
        self._items = getattr(self.repository, "_items", {})

    def list(self) -> list[FinanceiroTitulo]:
        return self.repository.list()

    def create(self, data: FinanceiroInput) -> FinanceiroTitulo:
        item = FinanceiroTitulo(id=f"fin_shadow_{uuid4().hex}", **data.model_dump())
        self.repository.add(item.id, item)
        return item

    def update(self, item_id: str, data: FinanceiroInput, expected_version: int) -> FinanceiroTitulo:
        # A operação CAS do repositório distingue registro ausente de versão obsoleta.
        # Não é necessário fazer uma leitura separada antes do UPDATE.
        item = FinanceiroTitulo(id=item_id, version=expected_version, **data.model_dump())
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

    def delete(self, item_id: str) -> None:
        if not self.repository.exists(item_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Título não encontrado.")
        self.repository.delete(item_id)

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
