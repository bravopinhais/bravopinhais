from uuid import uuid4
from fastapi import HTTPException, status
from .schemas import Usuario, UsuarioInput

class UsuariosService:
    def __init__(self) -> None:
        self._items: dict[str, Usuario] = {}

    def list(self) -> list[Usuario]:
        return list(self._items.values())

    def get(self, item_id: str) -> Usuario:
        item = self._items.get(item_id)
        if item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado.")
        return item

    def create(self, data: UsuarioInput) -> Usuario:
        email = data.email.lower()
        if any(item.email == email for item in self._items.values()):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Já existe um perfil vinculado a este e-mail.")
        item = Usuario(id=f"usr_shadow_{uuid4().hex}", **data.model_dump())
        self._items[item.id] = item
        return item

    def update(self, item_id: str, data: UsuarioInput) -> Usuario:
        current = self.get(item_id)
        email = data.email.lower()
        if any(item.id != item_id and item.email == email for item in self._items.values()):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Já existe um perfil vinculado a este e-mail.")
        item = Usuario(id=current.id, **data.model_dump())
        self._items[item_id] = item
        return item

    def delete(self, item_id: str) -> None:
        self.get(item_id)
        del self._items[item_id]

usuarios_service = UsuariosService()
