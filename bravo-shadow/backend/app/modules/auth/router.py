from fastapi import APIRouter, Depends

from app.core.authentication import get_current_principal
from app.core.authorization import AuthenticatedPrincipal, capabilities_for

router = APIRouter(prefix="/api/v1/auth", tags=["Autenticação"])


@router.get("/me")
async def current_user(
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> dict[str, object]:
    """Retorna somente a identidade já validada e o perfil interno."""
    return {
        "subject": principal.subject,
        "email": principal.email,
        "profile": principal.profile,
        "status": principal.account_status,
        "capabilities": list(capabilities_for(principal)),
    }
