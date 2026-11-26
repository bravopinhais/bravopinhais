from __future__ import annotations

from collections.abc import Callable
from threading import RLock
from typing import Generic, Protocol, TypeVar

T = TypeVar("T")
K = TypeVar("K")


class CollectionRepository(Protocol[T, K]):
    """Contrato de persistência para coleções de entidades."""

    def list(self) -> list[T]: ...
    def get(self, item_id: K) -> T | None: ...
    def add(self, item_id: K, item: T) -> None: ...
    def replace(self, item_id: K, item: T) -> None: ...
    def delete(self, item_id: K) -> None: ...
    def exists(self, item_id: K) -> bool: ...


class InMemoryCollectionRepository(Generic[T, K]):
    """Adaptador temporário; adequado a testes, não a produção/multi-worker."""

    def __init__(self) -> None:
        self._items: dict[K, T] = {}
        self._lock = RLock()

    def list(self) -> list[T]:
        with self._lock:
            return list(self._items.values())

    def get(self, item_id: K) -> T | None:
        with self._lock:
            return self._items.get(item_id)

    def add(self, item_id: K, item: T) -> None:
        with self._lock:
            if item_id in self._items:
                raise KeyError(f"Registro já existe: {item_id}")
            self._items[item_id] = item

    def replace(self, item_id: K, item: T) -> None:
        with self._lock:
            if item_id not in self._items:
                raise KeyError(f"Registro não existe: {item_id}")
            self._items[item_id] = item

    def delete(self, item_id: K) -> None:
        with self._lock:
            self._items.pop(item_id, None)

    def exists(self, item_id: K) -> bool:
        with self._lock:
            return item_id in self._items

    def any(self, predicate: Callable[[T], bool]) -> bool:
        with self._lock:
            return any(predicate(item) for item in self._items.values())
