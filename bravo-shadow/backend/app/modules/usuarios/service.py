from threading import RLock
from uuid import uuid4

from fastapi import HTTPException, status

from app.core.repositories import CollectionRepository, InMemoryCollectionRepository
from .schemas import Usuario, UsuarioInput


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

    def delete(self, item_id: str) -> None:
        self.get(item_id)
        self.repository.delete(item_id)


usuarios_service = UsuariosService()
