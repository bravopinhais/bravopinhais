from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

from app.core.postgres_cadastros import (
    PostgresContasBancariasRepository,
    PostgresEmpregadosRepository,
    PostgresFornecedoresRepository,
    PostgresMoradoresRepository,
)
from app.core.postgres_governance import (
    PostgresCondominioRepository,
    PostgresConselheirosRepository,
)
from app.core.postgres_catalogs import (
    PostgresCategoriasRepository,
    PostgresDocumentosRepository,
    PostgresMotivosAcertoRepository,
)
from app.core.postgres_inventory import (
    PostgresAcertosEstoqueRepository,
    PostgresEstoqueRepository,
)
from app.core.postgres_usuarios import PostgresUsuariosRepository
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
    operações de repositório. Cadastros financeiros, estoque, catálogos,
    documentos, moradores, fornecedores, empregados e contas bancárias usam
    adapters PostgreSQL; condomínio, conselho e perfis de usuário também usam PostgreSQL.
    """
    movement_repository = None
    if backend == "memory":
        formas_repository = InMemoryCollectionRepository()
        financeiro_repository = InMemoryCollectionRepository()
        plano_repository = InMemoryCollectionRepository()
        estoque_repository = InMemoryCollectionRepository()
        acertos_repository = InMemoryCollectionRepository()
        categorias_repository = InMemoryCollectionRepository()
        motivos_repository = InMemoryCollectionRepository()
        documentos_repository = InMemoryCollectionRepository()
        moradores_repository = InMemoryCollectionRepository()
        fornecedores_repository = InMemoryCollectionRepository()
        empregados_repository = InMemoryCollectionRepository()
        contas_bancarias_repository = InMemoryCollectionRepository()
        condominio_repository = InMemoryCollectionRepository()
        conselheiros_repository = InMemoryCollectionRepository()
        usuarios_repository = InMemoryCollectionRepository()
    elif backend == "postgres":
        if connection_factory is None:
            raise StorageConfigurationError(
                "O modo PostgreSQL exige uma connection_factory explícita. "
                "Nenhuma conexão foi tentada e não haverá fallback para memória."
            )
        formas_repository = PostgresFormasMonetariasRepository(connection_factory)
        financeiro_repository = PostgresFinanceiroRepository(connection_factory)
        plano_repository = PostgresPlanoContasRepository(connection_factory)
        estoque_repository = PostgresEstoqueRepository(connection_factory)
        acertos_repository = PostgresAcertosEstoqueRepository(connection_factory)
        categorias_repository = PostgresCategoriasRepository(connection_factory)
        motivos_repository = PostgresMotivosAcertoRepository(connection_factory)
        documentos_repository = PostgresDocumentosRepository(connection_factory)
        moradores_repository = PostgresMoradoresRepository(connection_factory)
        fornecedores_repository = PostgresFornecedoresRepository(connection_factory)
        empregados_repository = PostgresEmpregadosRepository(connection_factory)
        contas_bancarias_repository = PostgresContasBancariasRepository(connection_factory)
        condominio_repository = PostgresCondominioRepository(connection_factory)
        conselheiros_repository = PostgresConselheirosRepository(connection_factory)
        usuarios_repository = PostgresUsuariosRepository(connection_factory)
        movement_repository = acertos_repository
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

    estoque = EstoqueService(repository=estoque_repository)
    categorias = CategoriasService(repository=categorias_repository)
    documentos = DocumentosService(
        repository=documentos_repository,
        category_service=categorias,
    )
    categorias.set_reference_checker(documentos.has_category_reference)

    motivos_acerto = MotivosAcertoService(repository=motivos_repository)
    acertos_estoque = AcertosEstoqueService(
        repository=acertos_repository,
        inventory_service=estoque,
        reason_service=motivos_acerto,
        movement_repository=movement_repository,
    )
    motivos_acerto.set_reference_checker(acertos_estoque.has_reason_reference)
    estoque.set_movement_reference_checker(acertos_estoque.has_product_reference)

    moradores = MoradoresService(repository=moradores_repository)
    fornecedores = FornecedoresService(repository=fornecedores_repository)
    empregados = EmpregadosService(repository=empregados_repository)
    contas_bancarias = ContasBancariasService(repository=contas_bancarias_repository)
    condominio = CondominioService(repository=condominio_repository)
    conselheiros = ConselheirosService(repository=conselheiros_repository)
    usuarios = UsuariosService(repository=usuarios_repository)

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
