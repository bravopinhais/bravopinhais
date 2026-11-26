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
from app.modules.categorias.service import CategoriasService
from app.modules.condominio.service import CondominioService
from app.modules.conselheiros.service import ConselheirosService
from app.modules.contas_bancarias.service import ContasBancariasService
from app.modules.documentos.service import DocumentosService
from app.modules.empregados.service import EmpregadosService
from app.modules.estoque.service import EstoqueService
from app.modules.financeiro.service import FinanceiroService
from app.modules.formas_monetarias.service import FormasMonetariasService
from app.modules.fornecedores.service import FornecedoresService
from app.modules.moradores.service import MoradoresService
from app.modules.motivos_acerto.service import MotivosAcertoService
from app.modules.plano_contas.service import PlanoContasService
from app.modules.usuarios.service import UsuariosService

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
    categorias: CategoriasService
    motivos_acerto: MotivosAcertoService
    documentos: DocumentosService
    moradores: MoradoresService
    fornecedores: FornecedoresService
    empregados: EmpregadosService
    contas_bancarias: ContasBancariasService
    condominio: CondominioService
    conselheiros: ConselheirosService
    usuarios: UsuariosService


def build_storage_services(
    backend: StorageBackend,
    connection_factory: Callable[[], Any] | None = None,
) -> StorageServices:
    """Cria serviços isolados; nunca altera singletons ou estado global.

    No modo PostgreSQL, a fábrica é obrigatória e só será chamada durante
    operações de repositório. Estoque, catálogos, documentos, cadastros,
    condomínio, conselho e usuários seguem em memória até seus adaptadores
    serem implementados e testados.
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
    categorias = CategoriasService(repository=InMemoryCollectionRepository())
    documentos = DocumentosService(
        repository=InMemoryCollectionRepository(),
        category_service=categorias,
    )
    categorias.set_reference_checker(documentos.has_category_reference)

    motivos_acerto = MotivosAcertoService(repository=InMemoryCollectionRepository())
    acertos_estoque = AcertosEstoqueService(
        repository=InMemoryCollectionRepository(),
        inventory_service=estoque,
        reason_service=motivos_acerto,
    )
    motivos_acerto.set_reference_checker(acertos_estoque.has_reason_reference)

    moradores = MoradoresService(repository=InMemoryCollectionRepository())
    fornecedores = FornecedoresService(repository=InMemoryCollectionRepository())
    empregados = EmpregadosService(repository=InMemoryCollectionRepository())
    contas_bancarias = ContasBancariasService(repository=InMemoryCollectionRepository())
    condominio = CondominioService(repository=InMemoryCollectionRepository())
    conselheiros = ConselheirosService(repository=InMemoryCollectionRepository())
    usuarios = UsuariosService(repository=InMemoryCollectionRepository())

    return StorageServices(
        formas_monetarias=formas_monetarias,
        financeiro=financeiro,
        plano_contas=plano_contas,
        estoque=estoque,
        acertos_estoque=acertos_estoque,
        categorias=categorias,
        motivos_acerto=motivos_acerto,
        documentos=documentos,
        moradores=moradores,
        fornecedores=fornecedores,
        empregados=empregados,
        contas_bancarias=contas_bancarias,
        condominio=condominio,
        conselheiros=conselheiros,
        usuarios=usuarios,
    )
