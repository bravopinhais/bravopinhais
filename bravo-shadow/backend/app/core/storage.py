from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

from app.core.postgres_repositories import (
    PostgresFinanceiroRepository,
    PostgresFormasMonetariasRepository,
    PostgresPlanoContasRepository,
)
from app.core.repositories import InMemoryCollectionRepository
from app.modules.acertos_estoque.service import AcertosEstoqueService
from app.modules.estoque.service import EstoqueService
from app.modules.financeiro.service import FinanceiroService
from app.modules.formas_monetarias.service import FormasMonetariasService
from app.modules.plano_contas.service import PlanoContasService

StorageBackend = Literal["memory", "postgres"]


class StorageConfigurationError(RuntimeError):
    """Configuração de persistência ausente ou inválida."""


@dataclass(frozen=True)
class StorageServices:
    """Serviços pertencentes exclusivamente a uma instância da aplicação."""

    formas_monetarias: FormasMonetariasService
    financeiro: FinanceiroService
    plano_contas: PlanoContasService
    estoque: EstoqueService
    acertos_estoque: AcertosEstoqueService


def build_storage_services(
    backend: StorageBackend,
    connection_factory: Callable[[], Any] | None = None,
) -> StorageServices:
    """Cria serviços isolados; nunca altera singletons ou estado global.

    No modo PostgreSQL, a fábrica é obrigatória e só será chamada durante
    operações de repositório. Estoque e movimentos seguem em memória até que
    o adaptador transacional específico seja implementado e testado.
    """
    if backend == "memory":
        formas_repository = InMemoryCollectionRepository()
        financeiro_repository = InMemoryCollectionRepository()
        plano_repository = InMemoryCollectionRepository()
    elif backend == "postgres":
        if connection_factory is None:
            raise StorageConfigurationError(
                "O modo PostgreSQL exige uma connection_factory explícita. "
                "Nenhuma conexão foi tentada e não haverá fallback para memória."
            )
        formas_repository = PostgresFormasMonetariasRepository(connection_factory)
        financeiro_repository = PostgresFinanceiroRepository(connection_factory)
        plano_repository = PostgresPlanoContasRepository(connection_factory)
    else:
        raise StorageConfigurationError(
            "BRAVO_STORAGE_BACKEND deve ser 'memory' ou 'postgres'."
        )

    financeiro = FinanceiroService(repository=financeiro_repository)
    plano_contas = PlanoContasService(
        repository=plano_repository,
        has_financial_references=financeiro.has_plan_account_reference,
    )
    formas_monetarias = FormasMonetariasService(repository=formas_repository)

    estoque = EstoqueService(repository=InMemoryCollectionRepository())
    acertos_estoque = AcertosEstoqueService(
        repository=InMemoryCollectionRepository(),
        inventory_service=estoque,
    )

    return StorageServices(
        formas_monetarias=formas_monetarias,
        financeiro=financeiro,
        plano_contas=plano_contas,
        estoque=estoque,
        acertos_estoque=acertos_estoque,
    )
