from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Bravo Shadow API",
    description="API paralela do Bravo — ambiente de desenvolvimento e homologação.",
    version="0.1.0",
)

# CORS permanecerá restrito até que os domínios oficiais dos ambientes
# de desenvolvimento e homologação sejam definidos. Não usar "*" em produção.


@app.get("/api/v1/health", tags=["Sistema"])
async def health_check() -> dict[str, str]:
    """Confirma que a API sombra está ativa; não acessa dados de produção."""
    return {"status": "ok", "service": "bravo-shadow-api", "version": "0.1.0"}
