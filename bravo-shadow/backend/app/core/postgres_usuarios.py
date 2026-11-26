from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import HTTPException

from app.core.postgres import PostgresUnitOfWork
from app.modules.usuarios.schemas import Usuario


class PostgresUsuariosRepository:
    _table = "bravo_shadow.usuarios"
    _columns = "id, email, nome, loja, cargo, perfil, status"

    def __init__(self, connection_factory: Callable[[], Any]) -> None:
        self._uow = PostgresUnitOfWork(connection_factory)

    def _query(self, sql: str, params: tuple[Any, ...] = (), *, fetch: str = "none"):
        try:
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
        except Exception as exc:
            if getattr(exc, "sqlstate", None) == "23505":
                raise HTTPException(
                    status_code=409,
                    detail="Já existe um perfil vinculado a este e-mail.",
                ) from exc
            raise

    @staticmethod
    def _entity(row) -> Usuario | None:
        if row is None:
            return None
        return Usuario(
            id=row[0], email=row[1], nome=row[2], loja=row[3],
            cargo=row[4], perfil=row[5], status=row[6],
        )

    def list(self) -> list[Usuario]:
        rows = self._query(
            f"SELECT {self._columns} FROM {self._table} ORDER BY nome, id",
            fetch="all",
        )
        return [self._entity(row) for row in rows]

    def get(self, item_id: str) -> Usuario | None:
        return self._entity(self._query(
            f"SELECT {self._columns} FROM {self._table} WHERE id = %s",
            (item_id,), fetch="one",
        ))

    def exists(self, item_id: str) -> bool:
        return self.get(item_id) is not None

    def add(self, item_id: str, item: Usuario) -> None:
        self._query(
            f"INSERT INTO {self._table} (id, email, nome, loja, cargo, perfil, status) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (item_id, item.email, item.nome, item.loja, item.cargo, item.perfil, item.status),
        )

    def replace(self, item_id: str, item: Usuario) -> None:
        changed = self._query(
            f"UPDATE {self._table} SET email = %s, nome = %s, loja = %s, cargo = %s, "
            "perfil = %s, status = %s, updated_at = now(), version = version + 1 "
            "WHERE id = %s",
            (item.email, item.nome, item.loja, item.cargo, item.perfil, item.status, item_id),
        )
        if not changed:
            raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    def delete(self, item_id: str) -> None:
        changed = self._query(f"DELETE FROM {self._table} WHERE id = %s", (item_id,))
        if not changed:
            raise HTTPException(status_code=404, detail="Usuário não encontrado.")
