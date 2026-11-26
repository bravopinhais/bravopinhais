import os
from collections.abc import Callable
from typing import Any

from fastapi import FastAPI

from app.core.postgres_connection import create_postgres_connection_factory
from app.core.storage import StorageConfigurationError, configure_storage
from app.modules.contas_bancarias.router import router as contas_bancarias_router
from app.modules.condominio.router import router as condominio_router
from app.modules.conselheiros.router import router as conselheiros_router
from app.modules.moradores.router import router as moradores_router
from app.modules.categorias.router import router as categorias_router
from app.modules.motivos_acerto.router import router as motivos_acerto_router
from app.modules.estoque.router import router as estoque_router
from app.modules.acertos_estoque.router import router as acertos_estoque_router
from app.modules.documentos.router import router as documentos_router
from app.modules.financeiro.router import router as financeiro_router
from app.modules.fornecedores.router import router as fornecedores_router
from app.modules.empregados.router import router as empregados_router
from app.modules.formas_monetarias.router import router as formas_monetarias_router
from app.modules.plano_contas.router import router as plano_contas_router
from app.modules.usuarios.router import router as usuarios_router


def create_app(
    storage_backend: str | None = None,
    postgres_connection_factory: Callable[[], Any] | None = None,
) -> FastAPI:
    """Cria a API sombra com armazenamento explicitamente selecionado.

    Padrão seguro: memória. PostgreSQL só é selecionado quando solicitado e
    acompanhado de uma fábrica de conexão fornecida pelo ambiente hospedeiro.
    """
    selected_backend = (
        storage_backend or os.getenv("BRAVO_STORAGE_BACKEND", "memory")
    ).strip().lower()
    if selected_backend not in ("memory", "postgres"):
        raise StorageConfigurationError(
            "BRAVO_STORAGE_BACKEND deve ser 'memory' ou 'postgres'."
        )
    if selected_backend == "postgres" and postgres_connection_factory is None:
        try:
            postgres_connection_factory = create_postgres_connection_factory()
        except (RuntimeError, ValueError) as exc:
            raise StorageConfigurationError(str(exc)) from exc

    configured_backend = configure_storage(
        selected_backend, postgres_connection_factory
    )

    application = FastAPI(
        title="Bravo Shadow API",
        description="API paralela do Bravo — ambiente de desenvolvimento e homologação.",
        version="0.1.0",
    )
    application.state.storage_backend = configured_backend

    application.include_router(plano_contas_router)
    application.include_router(financeiro_router)
    application.include_router(formas_monetarias_router)
    application.include_router(contas_bancarias_router)
    application.include_router(fornecedores_router)
    application.include_router(empregados_router)
    application.include_router(condominio_router)
    application.include_router(conselheiros_router)
    application.include_router(moradores_router)
    application.include_router(categorias_router)
    application.include_router(motivos_acerto_router)
    application.include_router(estoque_router)
    application.include_router(acertos_estoque_router)
    application.include_router(documentos_router)
    application.include_router(usuarios_router)

    # CORS permanece fechado até definir a allowlist dos ambientes.
    # Não habilitar origem curinga em produção.

    @application.get("/api/v1/health", tags=["Sistema"])
    async def health_check() -> dict[str, str]:
        """Informa serviço e modo configurado; não testa nem acessa dados."""
        return {
            "status": "ok",
            "service": "bravo-shadow-api",
            "version": "0.1.0",
            "storage": configured_backend,
        }

    # A interface estática é servida pelo mesmo processo da API quando disponível.
    # No container, frontend/ fica ao lado de backend/ na raiz de bravo-shadow.
    from pathlib import Path
    from fastapi.staticfiles import StaticFiles

    frontend_dir = Path(__file__).resolve().parents[2] / "frontend"
    if frontend_dir.is_dir():
        application.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")

    return application


app = create_app()
