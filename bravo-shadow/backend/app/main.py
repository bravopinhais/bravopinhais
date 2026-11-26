from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.modules.contas_bancarias.router import router as contas_bancarias_router
from app.modules.condominio.router import router as condominio_router
from app.modules.conselheiros.router import router as conselheiros_router
from app.modules.moradores.router import router as moradores_router
from app.modules.categorias.router import router as categorias_router
from app.modules.motivos_acerto.router import router as motivos_acerto_router
from app.modules.estoque.router import router as estoque_router
from app.modules.acertos_estoque.router import router as acertos_estoque_router
from app.modules.financeiro.router import router as financeiro_router
from app.modules.financeiro.service import financeiro_service
from app.modules.fornecedores.router import router as fornecedores_router
from app.modules.empregados.router import router as empregados_router
from app.modules.formas_monetarias.router import router as formas_monetarias_router
from app.modules.plano_contas.router import router as plano_contas_router
from app.modules.plano_contas.service import plano_contas_service

# O checker consulta a coleção financeira de homologação em memória.
# Continua sem conexão com Supabase ou dados de produção.
plano_contas_service._has_financial_references = financeiro_service.has_plan_account_reference

app = FastAPI(
    title="Bravo Shadow API",
    description="API paralela do Bravo — ambiente de desenvolvimento e homologação.",
    version="0.1.0",
)

app.include_router(plano_contas_router)
app.include_router(financeiro_router)
app.include_router(formas_monetarias_router)
app.include_router(contas_bancarias_router)
app.include_router(fornecedores_router)
app.include_router(empregados_router)
app.include_router(condominio_router)
app.include_router(conselheiros_router)
app.include_router(moradores_router)
app.include_router(categorias_router)
app.include_router(motivos_acerto_router)
app.include_router(estoque_router)
app.include_router(acertos_estoque_router)

# CORS permanecerá restrito até que os domínios oficiais dos ambientes
# de desenvolvimento e homologação sejam definidos. Não usar "*" em produção.


@app.get("/api/v1/health", tags=["Sistema"])
async def health_check() -> dict[str, str]:
    """Confirma que a API sombra está ativa; não acessa dados de produção."""
    return {"status": "ok", "service": "bravo-shadow-api", "version": "0.1.0"}
