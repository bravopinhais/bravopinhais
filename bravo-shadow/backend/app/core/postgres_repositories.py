from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from typing import Any

from fastapi import HTTPException

from app.core.postgres import PostgresUnitOfWork
from app.modules.financeiro.schemas import FinanceiroTitulo
from app.modules.plano_contas.schemas import PlanoConta


class _PostgresRepository:
    """Base DB-API: uma transação curta por operação, sem fallback em memória."""

    def __init__(self, connection_factory: Callable[[], Any]) -> None:
        self._uow = PostgresUnitOfWork(connection_factory)

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

    def _replace_if_version(
        self,
        *,
        table: str,
        assignments: str,
        values: tuple[Any, ...],
        item_id: str,
        expected_version: int,
        missing_detail: str,
        conflict_detail: str,
    ) -> int:
        """Atualiza somente a versão lida; distingue 404 de conflito em uma transação."""
        with self._uow as uow:
            connection = uow.connection
            if connection is None:
                raise RuntimeError("A conexão PostgreSQL não foi aberta.")
            cursor = connection.cursor()
            try:
                cursor.execute(
                    f"UPDATE {table} SET {assignments}, updated_at = now(), "
                    "version = version + 1 WHERE id = %s AND version = %s",
                    (*values, item_id, expected_version),
                )
                if cursor.rowcount == 1:
                    return expected_version + 1
                cursor.execute(f"SELECT version FROM {table} WHERE id = %s", (item_id,))
                existing = cursor.fetchone()
                if existing is None:
                    raise HTTPException(status_code=404, detail=missing_detail)
                raise HTTPException(status_code=409, detail=conflict_detail)
            finally:
                cursor.close()

    @staticmethod
    def _sqlstate(error: Exception) -> str | None:
        return getattr(error, "sqlstate", None) or getattr(error, "pgcode", None)


class PostgresPlanoContasRepository(_PostgresRepository):
    """Adaptador PostgreSQL para Plano de Contas; requer schema bravo_shadow."""

    _columns = "id, codigo, nome, tipo, version"
    _table = "bravo_shadow.plano_contas"

    @staticmethod
    def _entity(row) -> PlanoConta | None:
        return PlanoConta(id=row[0], codigo=row[1], nome=row[2], tipo=row[3], version=row[4]) if row else None

    def list(self) -> list[PlanoConta]:
        rows = self._query(
            f"SELECT {self._columns} FROM {self._table} ORDER BY codigo",
            fetch="all",
        )
        return [self._entity(row) for row in rows]

    def get(self, item_id: str) -> PlanoConta | None:
        return self._entity(self._query(
            f"SELECT {self._columns} FROM {self._table} WHERE id = %s",
            (item_id,), fetch="one",
        ))

    def exists(self, item_id: str) -> bool:
        return self.get(item_id) is not None

    def add(self, item_id: str, item: PlanoConta) -> None:
        try:
            self._query(
                f"INSERT INTO {self._table} (id, codigo, nome, tipo) VALUES (%s, %s, %s, %s)",
                (item_id, item.codigo, item.nome, item.tipo),
            )
        except Exception as exc:
            if self._sqlstate(exc) == "23505":
                raise HTTPException(status_code=409, detail="Registro já existente.") from exc
            raise

    def replace(self, item_id: str, item: PlanoConta) -> None:
        try:
            changed = self._query(
                f"UPDATE {self._table} SET codigo = %s, nome = %s, tipo = %s, "
                "updated_at = now(), version = version + 1 WHERE id = %s",
                (item.codigo, item.nome, item.tipo, item_id),
            )
        except Exception as exc:
            if self._sqlstate(exc) == "23505":
                raise HTTPException(status_code=409, detail="Registro já existente.") from exc
            raise
        if not changed:
            raise HTTPException(status_code=404, detail="Conta não encontrada.")

    def replace_if_version(self, item_id: str, item: PlanoConta, expected_version: int) -> int:
        try:
            return self._replace_if_version(
                table=self._table,
                assignments="codigo = %s, nome = %s, tipo = %s",
                values=(item.codigo, item.nome, item.tipo),
                item_id=item_id,
                expected_version=expected_version,
                missing_detail="Conta não encontrada.",
                conflict_detail="A conta foi alterada por outra operação. Recarregue os dados antes de tentar novamente.",
            )
        except Exception as exc:
            if self._sqlstate(exc) == "23505":
                raise HTTPException(status_code=409, detail="Registro já existente.") from exc
            raise

    def delete(self, item_id: str) -> None:
        try:
            changed = self._query(f"DELETE FROM {self._table} WHERE id = %s", (item_id,))
        except Exception as exc:
            if self._sqlstate(exc) == "23503":
                raise HTTPException(
                    status_code=409,
                    detail="Esta conta possui lançamentos financeiros vinculados e não pode ser excluída.",
                ) from exc
            raise
        if not changed:
            raise HTTPException(status_code=404, detail="Conta não encontrada.")


class PostgresFinanceiroRepository(_PostgresRepository):
    """Adaptador PostgreSQL para títulos financeiros; valores permanecem Decimal."""

    _columns = "id, tipo, plano_conta_id, historico, valor, version"
    _table = "bravo_shadow.financeiro"

    @staticmethod
    def _entity(row) -> FinanceiroTitulo | None:
        if not row:
            return None
        return FinanceiroTitulo(
            id=row[0],
            tipo=row[1],
            planoContaId=row[2] or "",
            historico=row[3],
            valor=Decimal(row[4]),
        )

    def list(self) -> list[FinanceiroTitulo]:
        rows = self._query(
            f"SELECT {self._columns} FROM {self._table} ORDER BY created_at, id",
            fetch="all",
        )
        return [self._entity(row) for row in rows]

    def get(self, item_id: str) -> FinanceiroTitulo | None:
        return self._entity(self._query(
            f"SELECT {self._columns} FROM {self._table} WHERE id = %s",
            (item_id,), fetch="one",
        ))

    def exists(self, item_id: str) -> bool:
        return self.get(item_id) is not None

    def add(self, item_id: str, item: FinanceiroTitulo) -> None:
        self._query(
            f"INSERT INTO {self._table} (id, tipo, plano_conta_id, historico, valor) "
            "VALUES (%s, %s, %s, %s, %s)",
            (item_id, item.tipo, item.planoContaId or None, item.historico, item.valor),
        )

    def replace(self, item_id: str, item: FinanceiroTitulo) -> None:
        changed = self._query(
            f"UPDATE {self._table} SET tipo = %s, plano_conta_id = %s, "
            "historico = %s, valor = %s, updated_at = now(), version = version + 1 "
            "WHERE id = %s",
            (item.tipo, item.planoContaId or None, item.historico, item.valor, item_id),
        )
        if not changed:
            raise HTTPException(status_code=404, detail="Título não encontrado.")

    def replace_if_version(self, item_id: str, item: FinanceiroTitulo, expected_version: int) -> int:
        return self._replace_if_version(
            table=self._table,
            assignments="tipo = %s, plano_conta_id = %s, historico = %s, valor = %s",
            values=(item.tipo, item.planoContaId or None, item.historico, item.valor),
            item_id=item_id,
            expected_version=expected_version,
            missing_detail="Título não encontrado.",
            conflict_detail="O título foi alterado por outra operação. Recarregue os dados antes de tentar novamente.",
        )

    def delete(self, item_id: str) -> None:
        changed = self._query(f"DELETE FROM {self._table} WHERE id = %s", (item_id,))
        if not changed:
            raise HTTPException(status_code=404, detail="Título não encontrado.")

    def has_plan_account_reference(self, account_id: str) -> bool:
        row = self._query(
            f"SELECT 1 FROM {self._table} WHERE plano_conta_id = %s LIMIT 1",
            (account_id,), fetch="one",
        )
        return row is not None
