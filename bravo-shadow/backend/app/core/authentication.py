"""Autenticação Google para a API Bravo Shadow.

A camada valida o ID token no servidor e vincula o e-mail verificado
a um cadastro interno ativo. Os routers usam get_current_principal
como dependência de identidade antes de autorizar operações.
"""
import os
from collections.abc import Callable, Mapping
from typing import Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.authorization import AuthenticatedPrincipal
from app.modules.usuarios.service import UsuariosService

bearer_scheme = HTTPBearer(auto_error=False)


def verify_google_id_token(token: str) -> Mapping[str, Any]:
    """Valida assinatura, emissor, audiência e expiração usando google-auth."""
    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    if not client_id:
        raise RuntimeError("GOOGLE_CLIENT_ID não foi configurado.")

    from google.auth.transport.requests import Request as GoogleRequest
    from google.oauth2 import id_token

    return id_token.verify_oauth2_token(
        token,
        GoogleRequest(),
        audience=client_id,
    )


def principal_from_google_claims(
    claims: Mapping[str, Any],
    users_service: UsuariosService,
) -> AuthenticatedPrincipal:
    """Vincula claims verificados a perfil/status mantidos pelo Bravo."""
    subject = claims.get("sub")
    email = claims.get("email")
    email_verified = claims.get("email_verified")

    if (
        not isinstance(subject, str)
        or not subject.strip()
        or not isinstance(email, str)
        or not email.strip()
        or email_verified is not True
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identidade Google inválida ou e-mail não verificado.",
        )

    # Canonicaliza o identificador opaco antes de colocá-lo no principal/auditoria.
    subject = subject.strip()
    normalized_email = email.strip().lower()
    # Cadastros inconsistentes não podem transformar uma identidade válida
    # em erro 500; somente e-mails internos textuais participam da resolução.
    matches = [
        user
        for user in users_service.list()
        if isinstance(getattr(user, "email", None), str)
        and user.email.strip().lower() == normalized_email
    ]
    if len(matches) != 1 or matches[0].status != "Ativo":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário não cadastrado ou inativo no Bravo.",
        )

    user = matches[0]
    return AuthenticatedPrincipal(
        subject=subject,
        email=normalized_email,
        profile=user.perfil,
        account_status=user.status,
    )


async def get_current_principal(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthenticatedPrincipal:
    """Dependency reutilizável; exige Bearer ID token Google válido."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticação obrigatório.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    verifier: Callable[[str], Mapping[str, Any]] = getattr(
        request.app.state, "google_token_verifier", verify_google_id_token
    )
    try:
        claims = verifier(credentials.credentials)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Autenticação Google não configurada no servidor.",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token Google inválido ou expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    return principal_from_google_claims(claims, request.app.state.services.usuarios)
