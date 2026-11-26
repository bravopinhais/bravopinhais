from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.modules.contas_bancarias.router import router as contas_bancarias_router
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

# CORS permanecerá restrito até que os domínios oficiais dos ambientes
# de desenvolvimento e homologação sejam definidos. Não usar "*" em produção.


@app.get("/api/v1/health", tags=["Sistema"])
async def health_check() -> dict[str, str]:
    """Confirma que a API sombra está ativa; não acessa dados de produção."""
    return {"status": "ok", "service": "bravo-shadow-api", "version": "0.1.0"}
