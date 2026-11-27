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
        "usuarios:read", "usuarios:create", "usuarios:update", "usuarios:delete", "usuarios:deactivate",
    }
)

# A matriz Admin/Operador ainda não foi aprovada pelo responsável do Bravo.
# Por segurança, nenhum perfil recebe capacidades implicitamente. A aprovação
# deverá ser registrada e implementada em alteração isolada, acompanhada de testes.
# Movimentos de estoque não possuem UPDATE/DELETE no catálogo.
ROLE_CAPABILITIES = MappingProxyType(
    {
        "Admin": frozenset(),
        "Operador": frozenset(),
    }
)


def has_capability(
    principal: AuthenticatedPrincipal | None,
    capability: str,
) -> bool:
    """Retorna False em qualquer situação desconhecida ou não confiável."""
    if principal is None:
        return False
    if principal.account_status != "Ativo":
        return False
    if not isinstance(principal.subject, str) or not isinstance(principal.email, str):
        return False
    if not principal.subject.strip() or not principal.email.strip():
        return False
    if capability not in CAPABILITIES:
        return False
    return capability in ROLE_CAPABILITIES.get(principal.profile, frozenset())


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
        request: Request,
        principal: AuthenticatedPrincipal = Depends(get_current_principal),
    ) -> AuthenticatedPrincipal:
        try:
            require_capability(principal, capability)
        except HTTPException:
            # Só registrar quando há principal Google validado e subject útil.
            # Falhas de autenticação sem principal não recebem ator fictício.
            sink = getattr(request.app.state.services, "audit_sink", None)
            if (
                sink is not None
                and isinstance(principal.subject, str)
                and principal.subject.strip()
            ):
                event = AuditEvent(
                    actor_subject=principal.subject.strip(),
                    action=capability,
                    entity_type="authorization",
                    outcome="denied",
                    request_id=getattr(request.state, "request_id", None),
                )
                try:
                    sink.append(event)
                except Exception:
                    # A negação continua sendo 403; não mascarar nem liberar
                    # a operação por falha no registro da auditoria.
                    logger.exception("Falha ao persistir evento de negação de autorização.")
            raise
        return principal

    return dependency
