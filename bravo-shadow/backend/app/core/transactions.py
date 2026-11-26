from __future__ import annotations

from typing import Protocol, TypeVar

TMovement = TypeVar("TMovement")


class TransactionalInventoryRepository(Protocol[TMovement]):
    """Port para registrar um movimento e atualizar o saldo atomicamente.

    Implementações persistentes devem executar bloqueio da linha do produto,
    validação do saldo, atualização e inserção do histórico na mesma transação.
    Qualquer falha deve reverter todas as alterações.
    """

    def register_movement(
        self,
        *,
        product_id: str,
        movement: TMovement,
        delta: int,
        allow_negative: bool = False,
    ) -> TMovement:
        """Persiste o movimento e aplica delta ao saldo em uma única transação."""
        ...


class UnitOfWork(Protocol):
    """Contrato mínimo para delimitar uma unidade de trabalho transacional."""

    def __enter__(self) -> UnitOfWork: ...
    def __exit__(self, exc_type, exc, traceback) -> bool | None: ...
