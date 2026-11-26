from app.core.repositories import CollectionRepository, InMemoryCollectionRepository
from .schemas import Condominio, CondominioPatch


class CondominioService:
    def __init__(
        self,
        repository: CollectionRepository[dict[str, str], str] | None = None,
    ) -> None:
        self.repository = repository if repository is not None else InMemoryCollectionRepository()

    def get(self) -> Condominio:
        return Condominio(**(self.repository.get("singleton") or {}))

    def update(self, patch: CondominioPatch) -> Condominio:
        current = self.repository.get("singleton") or {}
        current.update({
            key: value
            for key, value in patch.model_dump(exclude_unset=True).items()
            if value is not None
        })
        if self.repository.exists("singleton"):
            self.repository.replace("singleton", current)
        else:
            self.repository.add("singleton", current)
        return self.get()


condominio_service = CondominioService()
