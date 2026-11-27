from threading import RLock
from uuid import uuid4

from fastapi import HTTPException, status

from app.core.audit import AuditEvent
from app.core.repositories import CollectionRepository, InMemoryCollectionRepository
from .schemas import (\n    Usuario, UsuarioAdministracaoInput, UsuarioCadastroInput,\n    UsuarioDadosCadastraisUpdateInput, UsuarioInput,\n)


class UsuariosService:
    def __init__(
        self,
        repository: CollectionRepository[Usuario, str] | None = None,
    ) -> None:
        self.repository = repository if repository is not None else InMemoryCollectionRepository()
        self._items = getattr(self.repository, "_items", {})
        self._email_lock = RLock()

    def list(self) -> list[Usuario]:
        return self.repository.list()

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

    def create_cadastral(self, data: UsuarioCadastroInput) -> Usuario:
        """Cria cadastro comum sem permitir atribuição de perfil privilegiado."""
        return self.create(
            UsuarioInput(
                **data.model_dump(),
                perfil="Operador",
                status="Ativo",
            )
        )

    def update_cadastral(
        self, item_id: str, data: UsuarioDadosCadastraisUpdateInput
    ) -> Usuario:
        """Atualiza apenas dados cadastrais; identidade e privilégios são preservados."""
        with self._email_lock:
            current = self.get(item_id)
            payload = data.model_dump(exclude_unset=True)
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

    def delete(self, item_id: str) -> None:
        self.get(item_id)
        self.repository.delete(item_id)

    def update_administrative_state(
        self,
        item_id: str,
        data: UsuarioAdministracaoInput,
        *,
        actor_subject: str,
        actor_email: str,
        audit_sink,
    ) -> None:
        """Executa alteração privilegiada somente em repositório transacional.

        Não está exposta por rota. O repositório deve persistir alteração e
        auditoria na mesma transação; adaptadores sem esse contrato falham
        fechados, sem mutar o cadastro.
        """
        if not actor_subject or not actor_subject.strip():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Identidade autenticada inválida.",
            )
        if not actor_email or not actor_email.strip():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="E-mail autenticado inválido.",
            )

        current = self.get(item_id)
        if current.email.strip().lower() == actor_email.strip().lower():
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
            actor_subject=actor_subject.strip(),
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
