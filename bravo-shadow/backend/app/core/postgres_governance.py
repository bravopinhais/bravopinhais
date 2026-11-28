from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import HTTPException

from app.core.audit import AuditEvent
from app.core.postgres import PostgresUnitOfWork
from app.modules.condominio.schemas import Condominio
from app.modules.conselheiros.schemas import Conselheiro


class _GovernanceRepository:
    def __init__(self, connection_factory: Callable[[], Any]) -> None:
        self._uow = PostgresUnitOfWork(connection_factory)

    def _execute_audited(self, sql: str, params: tuple[Any, ...], event: AuditEvent, audit_sink, *, missing_detail: str | None = None) -> None:
        append = getattr(audit_sink, "append_in_transaction", None)
        if not callable(append):
            raise HTTPException(status_code=503, detail="Auditoria transacional indisponível.")
        with self._uow as uow:
            connection = uow.connection
            if connection is None:
                raise RuntimeError("A conexão PostgreSQL não foi aberta.")
            cursor = connection.cursor()
            try:
                cursor.execute(sql, params)
                if missing_detail is not None and cursor.rowcount == 0:
                    raise HTTPException(status_code=404, detail=missing_detail)
                append(connection, event)
            finally:
                cursor.close()

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


class PostgresCondominioRepository(_GovernanceRepository):
    _table = "bravo_shadow.condominio"
    _fields = (
        "nome", "cnpj", "razaoSocial", "endereco", "bairro", "cidade", "uf",
        "cep", "telefone", "email", "copelBloco1", "copelBloco2",
        "copelBloco3", "copelBloco4", "copelAreasComuns", "gasSalao", "sanepar",
    )
    _columns = ", ".join(f'"{field}"' for field in _fields)

    def get(self, item_id: str) -> dict[str, str] | None:
        row = self._query(
            f"SELECT {self._columns} FROM {self._table} WHERE id = %s",
            (item_id,), fetch="one",
        )
        return dict(zip(self._fields, row)) if row else None

    def exists(self, item_id: str) -> bool:
        return self.get(item_id) is not None

    def add(self, item_id: str, item: dict[str, str]) -> None:
        fields = [field for field in self._fields if field in item]
        columns = ", ".join(['id', *(f'"{field}"' for field in fields)])
        placeholders = ", ".join(["%s"] * (len(fields) + 1))
        self._query(
            f"INSERT INTO {self._table} ({columns}) VALUES ({placeholders})",
            (item_id, *(item[field] for field in fields)),
        )

    def replace_audited(self, item_id: str, item: dict[str, str], event: AuditEvent, audit_sink) -> None:
        fields = [field for field in self._fields if field in item]
        if fields:
            columns = ", ".join(["id", *(f'"{field}"' for field in fields)])
            placeholders = ", ".join(["%s"] * (len(fields) + 1))
            assignments = ", ".join(
                f'"{field}" = EXCLUDED."{field}"' for field in fields
            )
            sql = (
                f"INSERT INTO {self._table} ({columns}) VALUES ({placeholders}) "
                f"ON CONFLICT (id) DO UPDATE SET {assignments}, "
                "updated_at = now(), version = bravo_shadow.condominio.version + 1"
            )
            params = ("singleton", *(item[field] for field in fields))
        else:
            sql = (
                f"INSERT INTO {self._table} (id) VALUES (%s) "
                "ON CONFLICT (id) DO NOTHING"
            )
            params = ("singleton",)
        self._execute_audited(sql, params, event, audit_sink)

    def replace(self, item_id: str, item: dict[str, str]) -> None:
        fields = [field for field in self._fields if field in item]
        if not fields:
            if not self.exists(item_id):
                raise HTTPException(status_code=404, detail="Condomínio não encontrado.")
            return
        assignments = ", ".join(f'"{field}" = %s' for field in fields)
        changed = self._query(
            f"UPDATE {self._table} SET {assignments}, updated_at = now(), "
            "version = version + 1 WHERE id = %s",
            (*(item[field] for field in fields), item_id),
        )
        if not changed:
            raise HTTPException(status_code=404, detail="Condomínio não encontrado.")


class PostgresConselheirosRepository(_GovernanceRepository):
    _table = "bravo_shadow.conselheiros"
    _columns = "id, nome, cargo, \"BlocoAp\", telefone"

    @staticmethod
    def _entity(row) -> Conselheiro | None:
        return Conselheiro(id=row[0], nome=row[1], cargo=row[2], BlocoAp=row[3], telefone=row[4]) if row else None

    def list(self) -> list[Conselheiro]:
        rows = self._query(
            f"SELECT {self._columns} FROM {self._table} ORDER BY nome, id",
            fetch="all",
        )
        return [self._entity(row) for row in rows]

    def get(self, item_id: str) -> Conselheiro | None:
        return self._entity(self._query(
            f"SELECT {self._columns} FROM {self._table} WHERE id = %s",
            (item_id,), fetch="one",
        ))

    def exists(self, item_id: str) -> bool:
        return self.get(item_id) is not None

    def add(self, item_id: str, item: Conselheiro) -> None:
        self._query(
            f"INSERT INTO {self._table} (id, nome, cargo, \"BlocoAp\", telefone) "
            "VALUES (%s, %s, %s, %s, %s)",
            (item_id, item.nome, item.cargo, item.BlocoAp, item.telefone),
        )

    def replace(self, item_id: str, item: Conselheiro) -> None:
        changed = self._query(
            f"UPDATE {self._table} SET nome = %s, cargo = %s, \"BlocoAp\" = %s, "
            "telefone = %s, updated_at = now(), version = version + 1 WHERE id = %s",
            (item.nome, item.cargo, item.BlocoAp, item.telefone, item_id),
        )
        if not changed:
            raise HTTPException(status_code=404, detail="Conselheiro não encontrado.")

    def add_audited(self, item_id: str, item: Conselheiro, event: AuditEvent, audit_sink) -> None:
        self._execute_audited(
            f"INSERT INTO {self._table} (id, nome, cargo, \"BlocoAp\", telefone) "
            "VALUES (%s, %s, %s, %s, %s)",
            (item_id, item.nome, item.cargo, item.BlocoAp, item.telefone),
            event, audit_sink,
        )

    def replace_audited(self, item_id: str, item: Conselheiro, event: AuditEvent, audit_sink) -> None:
        self._execute_audited(
            f"UPDATE {self._table} SET nome = %s, cargo = %s, \"BlocoAp\" = %s, "
            "telefone = %s, updated_at = now(), version = version + 1 WHERE id = %s",
            (item.nome, item.cargo, item.BlocoAp, item.telefone, item_id),
            event, audit_sink, missing_detail="Conselheiro não encontrado.",
        )

    def delete_audited(self, item_id: str, event: AuditEvent, audit_sink) -> None:
        self._execute_audited(
            f"DELETE FROM {self._table} WHERE id = %s", (item_id,),
            event, audit_sink, missing_detail="Conselheiro não encontrado.",
        )

    def delete(self, item_id: str) -> None:
        changed = self._query(f"DELETE FROM {self._table} WHERE id = %s", (item_id,))
        if not changed:
            raise HTTPException(status_code=404, detail="Conselheiro não encontrado.")
