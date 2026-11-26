from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any

from fastapi import HTTPException

from app.core.postgres import PostgresUnitOfWork
from app.modules.estoque.schemas import EstoqueItem
from app.modules.acertos_estoque.schemas import Acerto


class _InventoryPostgresBase:
    def __init__(self, connection_factory: Callable[[], Any]) -> None:
        self._uow = PostgresUnitOfWork(connection_factory)

    @staticmethod
    def _sqlstate(error: Exception) -> str | None:
        return getattr(error, "sqlstate", None) or getattr(error, "pgcode", None)

    def _query(self, sql: str, params: tuple[Any, ...] = (), *, fetch: str = "none"):
        with self._uow as uow:
            connection = uow.connection
            if connection is None:
                raise RuntimeError("A conexão PostgreSQL não foi aberta.")
            cursor = connection.cursor()
            try:
                cursor.execute(sql, params)
                if fetch == "all":
                    return cursor.fetchall()
                if fetch == "one":
                    return cursor.fetchone()
                return cursor.rowcount
            finally:
                cursor.close()


class PostgresEstoqueRepository(_InventoryPostgresBase):
    """CRUD de produtos no schema privado bravo_shadow."""

    _table = "bravo_shadow.estoque"
    _columns = (
        "id, item, quantidade, minimo, maximo, etiqueta, foto_nome, "
        "foto_compactada_gzip, marca, linha, fabricante, data_cadastro"
    )

    @staticmethod
    def _entity(row) -> EstoqueItem | None:
        if row is None:
            return None
        registered = row[11].isoformat() if isinstance(row[11], date) else (row[11] or "")
        return EstoqueItem(
            id=row[0], item=row[1], quantidade=row[2], minimo=row[3],
            maximo=row[4], etiqueta=row[5], fotoNome=row[6],
            fotoCompactadaGzip=row[7], marca=row[8], linha=row[9],
            fabricante=row[10], dataCadastro=registered,
        )

    def list(self) -> list[EstoqueItem]:
        rows = self._query(
            f"SELECT {self._columns} FROM {self._table} ORDER BY created_at, id",
            fetch="all",
        )
        return [self._entity(row) for row in rows]

    def get(self, item_id: str) -> EstoqueItem | None:
        return self._entity(self._query(
            f"SELECT {self._columns} FROM {self._table} WHERE id = %s",
            (item_id,), fetch="one",
        ))

    def exists(self, item_id: str) -> bool:
        return self.get(item_id) is not None

    @staticmethod
    def _values(item: EstoqueItem) -> tuple[Any, ...]:
        return (
            item.item, item.quantidade, item.minimo, item.maximo, item.etiqueta,
            item.fotoNome, item.fotoCompactadaGzip, item.marca, item.linha,
            item.fabricante, item.dataCadastro or None,
        )

    def add(self, item_id: str, item: EstoqueItem) -> None:
        self._query(
            f"INSERT INTO {self._table} "
            "(id, item, quantidade, minimo, maximo, etiqueta, foto_nome, "
            "foto_compactada_gzip, marca, linha, fabricante, data_cadastro) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (item_id, *self._values(item)),
        )

    def replace(self, item_id: str, item: EstoqueItem) -> None:
        values = self._values(item)
        changed = self._query(
            f"UPDATE {self._table} SET item = %s, quantidade = %s, minimo = %s, "
            "maximo = %s, etiqueta = %s, foto_nome = %s, foto_compactada_gzip = %s, "
            "marca = %s, linha = %s, fabricante = %s, data_cadastro = %s, "
            f"updated_at = now(), version = version + 1 WHERE id = %s",
            (*values, item_id),
        )
        if not changed:
            raise HTTPException(status_code=404, detail="Produto não encontrado.")

    def delete(self, item_id: str) -> None:
        try:
            changed = self._query(f"DELETE FROM {self._table} WHERE id = %s", (item_id,))
        except Exception as exc:
            if self._sqlstate(exc) == "23503":
                raise HTTPException(
                    status_code=409,
                    detail="O produto possui movimentações e não pode ser excluído.",
                ) from exc
            raise
        if not changed:
            raise HTTPException(status_code=404, detail="Produto não encontrado.")


class PostgresAcertosEstoqueRepository(_InventoryPostgresBase):
    """Histórico de movimentos; registra saldo e movimento atomicamente."""

    _table = "bravo_shadow.acertos_estoque"
    _columns = "id, data, tipo, produto_id, quantidade, motivo, motivo_id"

    @staticmethod
    def _entity(row) -> Acerto | None:
        if row is None:
            return None
        movement_date = row[1].isoformat() if hasattr(row[1], "isoformat") else str(row[1])
        return Acerto(
            id=row[0], data=movement_date, tipo=row[2], produtoId=row[3],
            quantidade=row[4], motivo=row[5], motivoId=row[6],
        )

    def list(self) -> list[Acerto]:
        rows = self._query(
            f"SELECT {self._columns} FROM {self._table} ORDER BY data, id",
            fetch="all",
        )
        return [self._entity(row) for row in rows]

    def get(self, item_id: str) -> Acerto | None:
        return self._entity(self._query(
            f"SELECT {self._columns} FROM {self._table} WHERE id = %s",
            (item_id,), fetch="one",
        ))

    def exists(self, item_id: str) -> bool:
        return self.get(item_id) is not None

    def add(self, item_id: str, item: Acerto) -> None:
        self._query(
            f"INSERT INTO {self._table} (id, data, tipo, produto_id, quantidade, motivo, motivo_id) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (item_id, item.data, item.tipo, item.produtoId, item.quantidade,
             item.motivo, item.motivoId),
        )

    def replace(self, item_id: str, item: Acerto) -> None:
        changed = self._query(
            f"UPDATE {self._table} SET data = %s, tipo = %s, produto_id = %s, "
            "quantidade = %s, motivo = %s, motivo_id = %s WHERE id = %s",
            (item.data, item.tipo, item.produtoId, item.quantidade,
             item.motivo, item.motivoId, item_id),
        )
        if not changed:
            raise HTTPException(status_code=404, detail="Acerto não encontrado.")

    def delete(self, item_id: str) -> None:
        changed = self._query(f"DELETE FROM {self._table} WHERE id = %s", (item_id,))
        if not changed:
            raise HTTPException(status_code=404, detail="Acerto não encontrado.")

    def register_movement(
        self, *, product_id: str, movement: Acerto, delta: int,
        allow_negative: bool = False,
    ) -> Acerto:
        """Bloqueia o produto e grava saldo + histórico no mesmo commit."""
        try:
            with self._uow as uow:
                connection = uow.connection
                if connection is None:
                    raise RuntimeError("A conexão PostgreSQL não foi aberta.")
                cursor = connection.cursor()
                try:
                    cursor.execute(
                        "SELECT quantidade FROM bravo_shadow.estoque WHERE id = %s FOR UPDATE",
                        (product_id,),
                    )
                    row = cursor.fetchone()
                    if row is None:
                        raise HTTPException(status_code=404, detail="Produto não encontrado.")
                    new_quantity = row[0] + delta
                    if new_quantity < 0 and not allow_negative:
                        raise HTTPException(
                            status_code=409,
                            detail="Quantidade de saída superior ao saldo disponível.",
                        )
                    cursor.execute(
                        "UPDATE bravo_shadow.estoque SET quantidade = %s, "
                        "updated_at = now(), version = version + 1 WHERE id = %s",
                        (new_quantity, product_id),
                    )
                    cursor.execute(
                        f"INSERT INTO {self._table} "
                        "(id, data, tipo, produto_id, quantidade, motivo, motivo_id) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                        (movement.id, movement.data, movement.tipo, movement.produtoId,
                         movement.quantidade, movement.motivo, movement.motivoId),
                    )
                    return movement
                finally:
                    cursor.close()
        except Exception as exc:
            if self._sqlstate(exc) == "23503":
                raise HTTPException(
                    status_code=409,
                    detail="O motivo informado não existe ou não pode ser removido durante a movimentação.",
                ) from exc
            raise
