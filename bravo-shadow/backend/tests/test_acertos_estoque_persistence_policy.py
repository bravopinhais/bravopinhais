import pytest
from fastapi import HTTPException

from app.core.repositories import InMemoryCollectionRepository
from app.modules.acertos_estoque.schemas import Acerto
from app.modules.acertos_estoque.service import AcertosEstoqueService


def make_movement():
    return Acerto(
        id="ac_1",
        data="2026-11-26T10:00:00-03:00",
        tipo="Entrada",
        produtoId="est_1",
        quantidade=2,
        motivo="Compra",
    )


def test_persisted_movement_cannot_be_deleted_destructively():
    repository = InMemoryCollectionRepository()
    movement = make_movement()
    repository.add(movement.id, movement)
    service = AcertosEstoqueService(
        repository=repository,
        movement_repository=object(),
    )

    with pytest.raises(HTTPException) as error:
        service.delete(movement.id)

    assert error.value.status_code == 409
    assert repository.get(movement.id) == movement


def test_missing_persisted_movement_still_returns_404():
    repository = InMemoryCollectionRepository()
    service = AcertosEstoqueService(
        repository=repository,
        movement_repository=object(),
    )

    with pytest.raises(HTTPException) as error:
        service.delete("missing")

    assert error.value.status_code == 404
