"""Política central de autorização da API Bravo Shadow.

Este módulo não autentica usuários nem valida tokens. O chamador só deve
construir AuthenticatedPrincipal após validar a identidade no servidor e
carregar perfil/status do cadastro confiável.
"""
from dataclasses import dataclass
from types import MappingProxyType

from fastapi import HTTPException, status


@dataclass(frozen=True, slots=True)
class AuthenticatedPrincipal:
    """Identidade já autenticada e resolvida no cadastro interno."""

    subject: str
    email: str
    profile: str
    account_status: str


# Capacidades granulares: o backend autoriza ações, não visibilidade de botões.
CAPABILITIES = frozenset(
    {
        "dashboard:read",
        "condominio:read", "condominio:update",
        "conselheiros:read", "conselheiros:create", "conselheiros:update", "conselheiros:delete",
        "plano_contas:read", "plano_contas:create", "plano_contas:update", "plano_contas:delete",
        "financeiro:read", "financeiro:create", "financeiro:update", "financeiro:delete",
        "formas_monetarias:read", "formas_monetarias:create", "formas_monetarias:update", "formas_monetarias:delete",
        "contas_bancarias:read", "contas_bancarias:create", "contas_bancarias:update", "contas_bancarias:delete",
        "moradores:read", "moradores:create", "moradores:update", "moradores:delete", "moradores:import",
        "fornecedores:read", "fornecedores:create", "fornecedores:update", "fornecedores:delete",
        "empregados:read", "empregados:create", "empregados:update", "empregados:delete",
        "categorias:read", "categorias:create", "categorias:delete",
        "motivos_estoque:read", "motivos_estoque:create", "motivos_estoque:delete",
        "estoque:read", "estoque:create", "estoque:update", "estoque:delete",
        "acertos_estoque:read", "acertos_estoque:create",
        "documentos:read", "documentos:create", "documentos:update", "documentos:delete",
        "relatorios:read",
        "configuracoes:read", "configuracoes:update",
        "usuarios:read", "usuarios:create", "usuarios:update", "usuarios:delete", "usuarios:deactivate",
    }
)

# Matriz aprovada pelo responsável do Bravo (2026-11-27).
# Admin: todas as capacidades explicitamente cadastradas em CAPABILITIES.
# Operador: rotina operacional; configurações e administração de usuários são
# somente leitura (quando aplicável) ou negadas. O backend é a fonte de verdade.
# Movimentos de estoque não possuem UPDATE/DELETE no catálogo.
ADMIN_CAPABILITIES = CAPABILITIES

OPERATOR_CAPABILITIES = frozenset(
    {
        "dashboard:read",
        # Consulta de cadastros/configurações, sem poder alterá-los.
        "condominio:read",
        "conselheiros:read",
        "plano_contas:read",
        "formas_monetarias:read",
        "contas_bancarias:read",
        "categorias:read",
        "motivos_estoque:read",
        # Operação diária.
        "financeiro:read", "financeiro:create", "financeiro:update",
        "financeiro:delete",
        "moradores:read", "moradores:create", "moradores:update",
        "moradores:delete", "moradores:import",
        "fornecedores:read", "fornecedores:create", "fornecedores:update",
        "fornecedores:delete",
        "empregados:read", "empregados:create", "empregados:update",
        "empregados:delete",
        "estoque:read", "estoque:create", "estoque:update", "estoque:delete",
        "acertos_estoque:read", "acertos_estoque:create",
        "documentos:read", "documentos:create", "documentos:update",
        "documentos:delete",
        "relatorios:read",
        "configuracoes:read",
    }
)

ROLE_CAPABILITIES = MappingProxyType(
    {
        "Admin": ADMIN_CAPABILITIES,
        "Operador": OPERATOR_CAPABILITIES,
    }
)


def has_capability(
    principal: AuthenticatedPrincipal | None,
    capability: str,
) -> bool:
    """Retorna False em qualquer situação desconhecida ou não confiável."""
    if not isinstance(principal, AuthenticatedPrincipal):
        return False
    if principal.account_status != "Ativo":
        return False
    if not isinstance(principal.profile, str):
        return False
    if not isinstance(principal.subject, str) or not isinstance(principal.email, str):
        return False
    if not principal.subject.strip() or not principal.email.strip():
        return False
    if not isinstance(capability, str) or capability not in CAPABILITIES:
        return False
    return capability in ROLE_CAPABILITIES.get(principal.profile, frozenset())



def capabilities_for(principal: AuthenticatedPrincipal | None) -> tuple[str, ...]:
    """Expõe somente capacidades explícitas do perfil interno ativo."""
    if (
        not isinstance(principal, AuthenticatedPrincipal)
        or principal.account_status != "Ativo"
        or not isinstance(principal.subject, str)
        or not principal.subject.strip()
        or not isinstance(principal.email, str)
        or not principal.email.strip()
    ):
        return ()
    return tuple(sorted(ROLE_CAPABILITIES.get(principal.profile, frozenset())))


def require_capability(
    principal: AuthenticatedPrincipal | None,
    capability: str,
) -> None:
    """Bloqueia a ação quando identidade, perfil ou capacidade não autorizam."""
    if not has_capability(principal, capability):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado para esta operação.",
        )



def require_capability_dependency(capability: str):
    """Cria uma dependência FastAPI para proteger uma rota por capacidade.

    A dependência autentica primeiro via get_current_principal e só então
    verifica a capacidade. A função é uma ferramenta de integração; não
    protege rotas até ser declarada explicitamente em cada endpoint.
    """
    import logging

    from fastapi import Depends, Request
    from app.core.audit import AuditEvent
    from app.core.authentication import get_current_principal

    logger = logging.getLogger("bravo.audit.authorization")

    def dependency(
        principal: AuthenticatedPrincipal = Depends(get_current_principal),
        request: Request = None,
    ) -> AuthenticatedPrincipal:
        try:
            require_capability(principal, capability)
        except HTTPException:
            # Só registrar quando há principal Google validado e subject útil.
            # Falhas de autenticação sem principal não recebem ator fictício.
            services = getattr(request.app.state, "services", None) if request is not None else None
            sink = getattr(services, "audit_sink", None)
            if (
                sink is not None
                and isinstance(principal, AuthenticatedPrincipal)
                and isinstance(principal.subject, str)
                and principal.subject.strip()
            ):
                event = AuditEvent(
                    actor_subject=principal.subject.strip(),
                    action=capability,
                    entity_type="authorization",
                    outcome="denied",
                    request_id=getattr(request.state, "request_id", None) if request is not None else None,
                )
                try:
                    sink.append(event)
                except Exception:
                    # Não registrar texto da exceção nem traceback: podem conter
                    # detalhes internos. A negação continua sendo 403.
                    logger.error(
                        "Falha ao persistir auditoria de negação; request_id=%s",
                        getattr(request.state, "request_id", None) if request is not None else None,
                    )
            raise
        # Contexto mínimo para o handler global de falhas inesperadas.
        # Nunca copiar e-mail, token, payload ou dados da rota para o contexto.
        if request is not None:
            request.state.authenticated_subject = principal.subject.strip()
        return principal

    # Metadado explícito para auditorias automatizadas da árvore de rotas.
    dependency.__bravo_required_capability__ = capability
    return dependency
