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
            if (
                getattr(exc, "sqlstate", None) == "23505"
                and getattr(getattr(exc, "diag", None), "constraint_name", None)
                == "usuarios_email_ci_uidx"
            ):
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

    def update_administrative_state(
        self,
        item_id: str,
        *,
        perfil: str,
        status: str,
        event: Any,
        audit_sink: Any,
    ) -> None:
        """Altera perfil/status e audita na mesma transação PostgreSQL.

        A operação permanece fora dos routers até aprovação da política e da
        matriz de capacidades. O bloqueio de tabela serializa mudanças
        administrativas concorrentes, inclusive quando afetam usuários
        diferentes, evitando corrida na proteção do último Admin ativo.
        """
        from app.core.audit import AuditEvent

        if perfil not in ("Admin", "Operador") or status not in ("Ativo", "Inativo"):
            raise ValueError("Perfil ou status administrativo inválido.")
        if not isinstance(event, AuditEvent):
            raise TypeError("Somente AuditEvent pode acompanhar a alteração.")
        if (
            event.action != "usuarios:update_administracao"
            or event.entity_type != "usuario"
            or event.entity_id != item_id
            or event.outcome != "success"
        ):
            raise ValueError("O evento de auditoria não corresponde à alteração.")
        if not callable(getattr(audit_sink, "append_in_transaction", None)):
            raise TypeError("audit_sink deve aceitar append_in_transaction.")

        try:
            with self._uow as uow:
                connection = uow.connection
                if connection is None:
                    raise RuntimeError("A conexão PostgreSQL não foi aberta.")
                cursor = connection.cursor()
                try:
                    # SHARE ROW EXCLUSIVE conflita com outro lock igual e com
                    # gravações concorrentes; a decisão é tomada sob o lock.
                    cursor.execute(
                        f"LOCK TABLE {self._table} IN SHARE ROW EXCLUSIVE MODE"
                    )
                    cursor.execute(
                        f"SELECT perfil, status FROM {self._table} WHERE id = %s FOR UPDATE",
                        (item_id,),
                    )
                    current = cursor.fetchone()
                    if current is None:
                        raise HTTPException(
                            status_code=404, detail="Usuário não encontrado."
                        )

                    removing_admin = (
                        current[0] == "Admin"
                        and current[1] == "Ativo"
                        and (perfil != "Admin" or status != "Ativo")
                    )
                    if removing_admin:
                        cursor.execute(
                            f"SELECT count(*) FROM {self._table} "
                            "WHERE perfil = 'Admin' AND status = 'Ativo'"
                        )
                        count_row = cursor.fetchone()
                        active_admins = int(count_row[0]) if count_row else 0
                        if active_admins <= 1:
                            raise HTTPException(
                                status_code=409,
                                detail="Não é permitido remover o último Admin ativo.",
                            )

                    cursor.execute(
                        f"UPDATE {self._table} SET perfil = %s, status = %s, "
                        "updated_at = now(), version = version + 1 WHERE id = %s",
                        (perfil, status, item_id),
                    )
                    if not cursor.rowcount:
                        raise HTTPException(
                            status_code=404, detail="Usuário não encontrado."
                        )
                    audit_sink.append_in_transaction(connection, event)
                finally:
                    cursor.close()
        except Exception as exc:
            if (
                getattr(exc, "sqlstate", None) == "23505"
                and getattr(getattr(exc, "diag", None), "constraint_name", None)
                == "usuarios_email_ci_uidx"
            ):
                raise HTTPException(
                    status_code=409,
                    detail="Já existe um perfil vinculado a este e-mail.",
                ) from exc
            raise
