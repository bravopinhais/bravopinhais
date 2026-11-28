from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status

from app.core.audit import AuditEvent

from app.core.authorization import AuthenticatedPrincipal, require_capability_dependency

from app.core.etag import format_etag, parse_if_match
from .schemas import FinanceiroInput, FinanceiroTitulo
from .service import FinanceiroService

router = APIRouter(prefix="/api/v1/financeiro", tags=["Financeiro"])

def get_service(request: Request) -> FinanceiroService:
    return request.app.state.services.financeiro


def audit_financial_read(request: Request, actor: AuthenticatedPrincipal) -> None:
    """Registra consultas financeiras sem copiar valores ou históricos."""
    sink = getattr(get_service(request), "audit_sink", None)
    if sink is None:
        return
    event = AuditEvent(
        actor_subject=actor.subject.strip(),
        action="financeiro:list",
        entity_type="financeiro",
        outcome="success",
        request_id=getattr(request.state, "request_id", None),
    )
    try:
        sink.append(event)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auditoria indisponível. A consulta financeira não foi concluída.",
        ) from exc


@router.get("", response_model=list[FinanceiroTitulo])
def list_titles(
    request: Request,
    principal: AuthenticatedPrincipal = Depends(require_capability_dependency("financeiro:read")),
) -> list[FinanceiroTitulo]:
    audit_financial_read(request, principal)
    return get_service(request).list()


@router.post("", response_model=FinanceiroTitulo, status_code=status.HTTP_201_CREATED)
def create_title(
    data: FinanceiroInput,
    request: Request,
    response: Response,
    _principal: AuthenticatedPrincipal = Depends(require_capability_dependency("financeiro:create")),
):
    item = get_service(request).create(
        data, actor=_principal, request_id=getattr(request.state, "request_id", None)
    )
    response.headers["ETag"] = format_etag(item.version)
    return item


@router.put("/{item_id}", response_model=FinanceiroTitulo)
def update_title(
    item_id: str,
    data: FinanceiroInput,
    request: Request,
    response: Response,
    if_match: str | None = Header(default=None, alias="If-Match"),
    _principal: AuthenticatedPrincipal = Depends(require_capability_dependency("financeiro:update")),
):
    expected_version = parse_if_match(if_match)
    item = get_service(request).update(
        item_id, data, expected_version,
        actor=_principal, request_id=getattr(request.state, "request_id", None),
    )
    response.headers["ETag"] = format_etag(item.version)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_title(
    item_id: str,
    request: Request,
    _principal: AuthenticatedPrincipal = Depends(require_capability_dependency("financeiro:delete")),
) -> None:
    get_service(request).delete(
        item_id, actor=_principal, request_id=getattr(request.state, "request_id", None)
    )
