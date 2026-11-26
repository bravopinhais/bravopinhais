from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal

from app.core.postgres_repositories import (
    PostgresFinanceiroRepository,\n    PostgresFormasMonetariasRepository,
    PostgresPlanoContasRepository,
)
from app.core.repositories import InMemoryCollectionRepository
from app.modules.financeiro.service import financeiro_service\nfrom app.modules.formas_monetarias.service import formas_monetarias_service
from app.modules.plano_contas.service import plano_contas_service

StorageBackend = Literal["memory", "postgres"]


class StorageConfigurationError(RuntimeError):
    """Configuração de persistência ausente ou inválida."""


def configure_storage(
    backend: StorageBackend,
    connection_factory: Callable[[], Any] | None = None,
) -> str:
    """Injeta os repositórios dos módulos persistidos sem fallback implícito.

    O modo PostgreSQL exige uma fábrica de conexão fornecida pelo ambiente.
    Este módulo não importa driver, lê credenciais ou abre conexão por conta
    própria. Os demais módulos permanecem em memória nesta fase.
    """
    if backend == "memory":
        formas_monetarias_service.repository = InMemoryCollectionRepository()\n        formas_monetarias_service._items = formas_monetarias_service.repository._items\n        financeiro_service.repository = InMemoryCollectionRepository()
        financeiro_service._items = financeiro_service.repository._items
        plano_contas_service.repository = InMemoryCollectionRepository()
        plano_contas_service._items = plano_contas_service.repository._items
        plano_contas_service._has_financial_references = (
            financeiro_service.has_plan_account_reference
        )
        return "memory"

    if backend != "postgres":
        raise StorageConfigurationError(
            "BRAVO_STORAGE_BACKEND deve ser 'memory' ou 'postgres'."
        )
    if connection_factory is None:
        raise StorageConfigurationError(
            "O modo PostgreSQL exige uma connection_factory explícita. "
            "Nenhuma conexão foi tentada e não haverá fallback para memória."
        )

    # Construção explícita: as operações só abrirão conexão quando chamadas.
    formas_repository = PostgresFormasMonetariasRepository(connection_factory)\n    financeiro_repository = PostgresFinanceiroRepository(connection_factory)
    plano_repository = PostgresPlanoContasRepository(connection_factory)

    formas_monetarias_service.repository = formas_repository\n    formas_monetarias_service._items = {}\n    financeiro_service.repository = financeiro_repository
    financeiro_service._items = {}
    plano_contas_service.repository = plano_repository
    plano_contas_service._items = {}
    plano_contas_service._has_financial_references = (
        financeiro_service.has_plan_account_reference
    )
    return "postgres"
