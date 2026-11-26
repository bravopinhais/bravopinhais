from .schemas import Condominio, CondominioPatch

class CondominioService:
    def __init__(self) -> None:
        self._data: dict[str, str] = {}
    def get(self) -> Condominio:
        return Condominio(**self._data)
    def update(self, patch: CondominioPatch) -> Condominio:
        # Merge only supplied fields to preserve fields outside the current form.
        self._data.update({key: value for key, value in patch.model_dump(exclude_unset=True).items() if value is not None})
        return self.get()

condominio_service = CondominioService()
