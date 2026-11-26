from dataclasses import asdict

from fastapi import APIRouter, Depends, Request

from app.core.authorization import require_capability_dependency

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard"])


@router.get(
    "/resumo",
    dependencies=[Depends(require_capability_dependency("dashboard:read"))],
)
def dashboard_summary(request: Request):
    return asdict(request.app.state.dashboard_service.summary())
