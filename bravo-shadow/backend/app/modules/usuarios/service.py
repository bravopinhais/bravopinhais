from __future__ import annotations

from threading import RLock
from uuid import uuid4

from fastapi import HTTPException, status

from app.core.audit import AuditEvent
from app.core.authorization import AuthenticatedPrincipal
from app.core.repositories import CollectionRepository, InMemoryCollectionRepository
from .schemas import (
    Usuario, UsuarioAdministracaoInput, UsuarioCadastroInput,
    UsuarioDadosCadastraisUpdateInput, UsuarioInput,
)


class UsuariosService:
    def __init__(
        self,
        repository: CollectionRepository[Usuario, str] | None = None,
        audit_sink=None,
    ) -> None:
        self.repository = repository if repository is not None else InMemoryCollectionRepository()
        self.audit_sink = audit_sink
        self._items = getattr(self.repository, "_items", {})
        self._email_lock = RLock()

    def list(self) -> list[Usuario]:
        return self.repository.list()

    def find_by_email(self, email: str) -> list[Usuario]:
        """Resolve e-mail sem carregar todo o cadastro quando o adapter oferece busca indexada."""
        normalized = email.strip().lower()
        if not normalized:
            return []
        operation = getattr(self.repository, "find_by_email", None)
        if callable(operation):
            return operation(normalized)
        return [
            user for user in self.repository.list()
            if isinstance(getattr(user, "email", None), str)
            and user.email.strip().lower() == normalized
        ]

    def get(self, item_id: str) -> Usuario:
        item = self.repository.get(item_id)
        if item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado.")
        return item

    def _ensure_email_available(self, email: str, excluding_id: str | None = None) -> None:
        normalized = email.strip().lower()
        if any(item.id != excluding_id and item.email.lower() == normalized for item in self.repository.list()):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Já existe um perfil vinculado a este e-mail.")

    def create(self, data: UsuarioInput) -> Usuario:
        # O adaptador em memória é single-process; a seção crítica torna a
        # verificação de unicidade + gravação atômica dentro desta instância.
        with self._email_lock:
            self._ensure_email_available(data.email)
            payload = data.model_dump()
            payload["email"] = data.email.strip().lower()
            item = Usuario(id=f"usr_shadow_{uuid4().hex}", **payload)
            self.repository.add(item.id, item)
            return item

    def update(self, item_id: str, data: UsuarioInput) -> Usuario:
        with self._email_lock:
            current = self.get(item_id)
            self._ensure_email_available(data.email, excluding_id=item_id)
            payload = data.model_dump()
            payload["email"] = data.email.strip().lower()
            item = Usuario(id=current.id, **payload)
            self.repository.replace(item_id, item)
            return item

    def create_cadastral(
        self, data: UsuarioCadastroInput, *, actor: AuthenticatedPrincipal | None = None,
        request_id: str | None = None,
    ) -> Usuario:
        """Cria cadastro comum; em armazenamento persistente exige auditoria atômica."""
        if self.audit_sink is not None and actor is None:
            raise HTTPException(status_code=403, detail="Identidade autenticada obrigatória para criar usuários.")
        item = Usuario(
            id=f"usr_shadow_{uuid4().hex}",
            **data.model_dump(), perfil="Operador", status="Ativo",
        )
        if actor is not None:
            if not isinstance(actor, AuthenticatedPrincipal) or actor.account_status != "Ativo" or not actor.subject.strip():
                raise HTTPException(status_code=403, detail="Ator administrativo inválido.")
            operation = getattr(self.repository, "add_audited", None)
            if not callable(operation) or not callable(getattr(self.audit_sink, "append_in_transaction", None)):
                raise HTTPException(status_code=503, detail="Criação auditada de usuários indisponível.")
            event = AuditEvent(
                actor_subject=actor.subject.strip(), action="usuarios:create",
                entity_type="usuario", entity_id=item.id, outcome="success", request_id=request_id,
            )
            operation(item, event=event, audit_sink=self.audit_sink)
        else:
            self.repository.add(item.id, item)
        return item

    def update_cadastral(
        self, item_id: str, data: UsuarioDadosCadastraisUpdateInput, *,
        actor: AuthenticatedPrincipal | None = None, request_id: str | None = None,
    ) -> Usuario:
        """Atualiza apenas dados cadastrais e audita na mesma transação no PostgreSQL."""
        if self.audit_sink is not None and actor is None:
            raise HTTPException(status_code=403, detail="Identidade autenticada obrigatória para atualizar usuários.")
        with self._email_lock:
            payload = data.model_dump(exclude_unset=True)
            operation = getattr(self.repository, "update_cadastral", None)
            if callable(operation):
                if actor is not None:
                    if not isinstance(actor, AuthenticatedPrincipal) or actor.account_status != "Ativo" or not actor.subject.strip():
                        raise HTTPException(status_code=403, detail="Ator administrativo inválido.")
                    audited = getattr(self.repository, "update_cadastral_audited", None)
                    if not callable(audited) or not callable(getattr(self.audit_sink, "append_in_transaction", None)):
                        raise HTTPException(status_code=503, detail="Atualização cadastral auditada indisponível.")
                    event = AuditEvent(
                        actor_subject=actor.subject.strip(), action="usuarios:update_cadastral",
                        entity_type="usuario", entity_id=item_id, outcome="success", request_id=request_id,
                    )
                    return audited(item_id, event=event, audit_sink=self.audit_sink, **payload)
                # O adapter PostgreSQL atualiza somente as colunas permitidas.
                # Não ler e reenviar perfil/status evita restaurar estado obsoleto
                # após uma alteração administrativa concorrente.
                return operation(item_id, **payload)

            current = self.get(item_id)
            updated = Usuario(
                id=current.id,
                email=current.email,
                nome=payload.get("nome", current.nome),
                loja=payload.get("loja", current.loja),
                cargo=payload.get("cargo", current.cargo),
                perfil=current.perfil,
                status=current.status,
            )
            self.repository.replace(item_id, updated)
            return updated

    def deactivate(
        self, item_id: str, *, actor: AuthenticatedPrincipal,
        request_id: str | None = None,
    ) -> None:
        """Desativa sem apagar o cadastro; exige auditoria na mesma transação."""
        if (not isinstance(actor, AuthenticatedPrincipal) or actor.account_status != "Ativo"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Identidade autenticada inválida ou inativa.",
            )
        if not isinstance(actor.subject, str) or not actor.subject.strip():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Identidade autenticada inválida.",
            )
        if not isinstance(actor.email, str) or not actor.email.strip():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="E-mail autenticado inválido.",
            )

        current = self.get(item_id)
        if current.email.strip().lower() == actor.email.strip().lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Não é permitido desativar a própria conta.",
            )
        operation = getattr(self.repository, "deactivate_user", None)
        if not callable(operation) or not callable(
            getattr(self.audit_sink, "append_in_transaction", None)
        ):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Desativação auditada indisponível neste armazenamento.",
            )

        event = AuditEvent(
            actor_subject=actor.subject.strip(),
            action="usuarios:desativar",
            entity_type="usuario",
            entity_id=item_id,
            outcome="success",
            request_id=request_id,
        )
        operation(item_id, event=event, audit_sink=self.audit_sink)

    def delete(self, item_id: str) -> None:
        """Bloqueia exclusão física também na camada de serviço."""
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Exclusão física indisponível. Use a operação de desativação lógica.",
        )

    def update_administrative_state(
        self,
        item_id: str,
        data: UsuarioAdministracaoInput,
        *,
        actor: AuthenticatedPrincipal,
        audit_sink,
    ) -> None:
        """Executa alteração privilegiada somente em repositório transacional.

        Não está exposta por rota. O repositório deve persistir alteração e
        auditoria na mesma transação; adaptadores sem esse contrato falham
        fechados, sem mutar o cadastro.
        """
        if (
            not isinstance(actor, AuthenticatedPrincipal)
            or actor.account_status != "Ativo"
            or not isinstance(actor.subject, str)
            or not actor.subject.strip()
            or not isinstance(actor.email, str)
            or not actor.email.strip()
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Identidade autenticada inválida ou inativa.",
            )
        if actor.profile != "Admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Somente Admin pode alterar perfil ou status de usuários.",
            )

        current = self.get(item_id)
        if current.email.strip().lower() == actor.email.strip().lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Não é permitido alterar o próprio perfil ou status.",
            )

        operation = getattr(self.repository, "update_administrative_state", None)
        if not callable(operation):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Alteração administrativa transacional indisponível neste armazenamento.",
            )

        event = AuditEvent(
            actor_subject=actor.subject.strip(),
            action="usuarios:update_administracao",
            entity_type="usuario",
            entity_id=item_id,
            outcome="success",
        )
        operation(
            item_id,
            perfil=data.perfil,
            status=data.status,
            event=event,
            audit_sink=audit_sink,
        )


usuarios_service = UsuariosService()
