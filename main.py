"""Vercel entrypoint for the isolated Bravo Shadow preview.

The hosted API fails closed until PostgreSQL and Google identity configuration
are explicitly present. Local tests continue to import backend/app directly.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "bravo-shadow" / "backend"
FRONTEND = ROOT / "bravo-shadow" / "frontend"

# The existing backend uses the "app" package from backend/.
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

_required = {
    "BRAVO_STORAGE_BACKEND": os.getenv("BRAVO_STORAGE_BACKEND", "").strip().lower() == "postgres",
    "BRAVO_DATABASE_URL": bool(os.getenv("BRAVO_DATABASE_URL", "").strip()),
    "GOOGLE_CLIENT_ID": bool(os.getenv("GOOGLE_CLIENT_ID", "").strip()),
}

# Exportação direta exigida pela detecção estática do runtime FastAPI da Vercel.
# A instância é substituída pela aplicação completa somente quando a configuração
# segura estiver presente; sem ela, o bloco abaixo mantém a API bloqueada.
app = FastAPI(
    title="Bravo Shadow — inicialização segura",
    description="Aplicação isolada com inicialização fail-closed.",
    version="0.1.0",
)

if all(_required.values()):
    # Import the complete API only after all production-like prerequisites exist.
    # This prevents Vercel from silently starting the in-memory test backend.
    from app.main import app  # noqa: E402
else:
    app = FastAPI(
        title="Bravo Shadow — configuração pendente",
        description="Prévia isolada; API bloqueada até a configuração segura do PostgreSQL e Google.",
        version="0.1.0",
    )

    @app.get("/api/v1/health", tags=["Sistema"])
    async def health_check() -> JSONResponse:
        missing = [name for name, configured in _required.items() if not configured]
        return JSONResponse(
            status_code=503,
            content={
                "status": "blocked",
                "service": "bravo-shadow-api",
                "storage": "not-configured",
                "reason": "A API permanece bloqueada até a configuração segura do ambiente.",
                "missing_configuration": missing,
            },
        )

    @app.api_route(
        "/api/{path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    )
    async def api_not_configured(path: str, request: Request) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={
                "detail": "API Shadow ainda não configurada. Nenhuma operação foi executada.",
                "service": "bravo-shadow-api",
            },
        )

    if FRONTEND.is_dir():
        app.mount("/", StaticFiles(directory=str(FRONTEND), html=True), name="frontend")
