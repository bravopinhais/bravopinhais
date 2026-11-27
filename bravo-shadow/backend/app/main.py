import os
from collections.abc import Callable
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Request

from app.core.postgres_connection import create_postgres_connection_factory
from app.core.storage import StorageConfigurationError, build_storage_services
from app.modules.auth.router import router as auth_router
from app.modules.dashboard.service import DashboardService
from app.modules.dashboard.router import router as dashboard_router
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

    Padrão seguro: memória. PostgreSQL só é selecionado quando solicitado; a fábrica
    pode ser injetada pelo hospedeiro ou criada a partir de BRAVO_DATABASE_URL.
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

    services = build_storage_services(
        selected_backend, postgres_connection_factory
    )

    application = FastAPI(
        title="Bravo Shadow API",
        description="API paralela do Bravo — ambiente de desenvolvimento e homologação.",
        version="0.1.0",
    )
    @application.middleware("http")
    async def assign_request_id(request: Request, call_next):
        # O identificador é sempre gerado pelo servidor; cabeçalhos recebidos
        # do cliente não podem escolher nem sobrescrever o contexto de auditoria.
        request_id = f"req_{uuid4().hex}"
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    application.state.storage_backend = selected_backend
    application.state.services = services
    application.state.dashboard_service = DashboardService(
        formas_monetarias=services.formas_monetarias,
        plano_contas=services.plano_contas,
        financeiro=services.financeiro,
        estoque=services.estoque,
        moradores=services.moradores,
        fornecedores=services.fornecedores,
        empregados=services.empregados,
        documentos=services.documentos,
    )

    application.include_router(auth_router)
    application.include_router(dashboard_router)
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
            "storage": selected_backend,
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
