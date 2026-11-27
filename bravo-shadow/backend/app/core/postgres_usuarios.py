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

    @staticmethod
    def _close_cursor(cursor: Any) -> None:
        """Fecha o cursor sem esconder uma falha anterior da consulta."""
        import sys

        primary_error = sys.exception()
        try:
            cursor.close()
        except BaseException as close_error:
            if primary_error is None:
                raise
            add_note = getattr(primary_error, "add_note", None)
            if callable(add_note):
                add_note(
                    "Falha secundária durante fechamento do cursor: "
                    f"{type(close_error).__name__}."
                )

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
                    self._close_cursor(cursor)
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

    def find_by_email(self, normalized_email: str) -> list[Usuario]:
        """Busca no máximo dois resultados; duplicidade deve bloquear autenticação."""
        rows = self._query(
            f"SELECT {self._columns} FROM {self._table} "
            "WHERE lower(email) = %s ORDER BY id LIMIT 2",
            (normalized_email.strip().lower(),),
            fetch="all",
        )
        return [self._entity(row) for row in rows]

    def exists(self, item_id: str) -> bool:
        return self.get(item_id) is not None

    def add(self, item_id: str, item: Usuario) -> None:
        """Insere somente usuário comum; privilégios exigem fluxo dedicado."""
        if item.perfil != "Operador" or item.status != "Ativo":
            raise ValueError(
                "Criação genérica aceita somente Operador/Ativo; "
                "privilégios exigem operação administrativa controlada."
            )
        self._query(
            f"INSERT INTO {self._table} (id, email, nome, loja, cargo, perfil, status) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (item_id, item.email, item.nome, item.loja, item.cargo, "Operador", "Ativo"),
        )

    def replace(self, item_id: str, item: Usuario) -> None:
        """Bloqueia substituição ampla que poderia sobrescrever estado privilegiado."""
        raise RuntimeError(
            "Substituição genérica de usuário desabilitada no PostgreSQL; "
            "use update_cadastral ou a operação administrativa transacional."
        )

    def update_cadastral(
        self,
        item_id: str,
        *,
        nome: str | None = None,
        loja: str | None = None,
        cargo: str | None = None,
    ) -> Usuario:
        """Atualiza somente colunas cadastrais, sem regravar privilégios."""
        allowed = {"nome": nome, "loja": loja, "cargo": cargo}
        assignments = [
            (column, value)
            for column, value in allowed.items()
            if value is not None
        ]
        if not assignments:
            raise ValueError("Informe ao menos um campo cadastral para atualizar.")

        set_clause = ", ".join(f"{column} = %s" for column, _ in assignments)
        params = tuple(value for _, value in assignments) + (item_id,)
        sql = (
            f"UPDATE {self._table} SET {set_clause}, "
            "updated_at = now(), version = version + 1 "
            f"WHERE id = %s RETURNING {self._columns}"
        )
        with self._uow as uow:
            connection = uow.connection
            if connection is None:
                raise RuntimeError("A conexão PostgreSQL não foi aberta.")
            cursor = connection.cursor()
            try:
                # Serializa atualizações cadastrais com mudanças administrativas.
                # Ambas alteram o mesmo registro e devem concluir em uma ordem
                # definida antes de calcular a próxima versão persistida.
                cursor.execute(
                    f"LOCK TABLE {self._table} IN SHARE ROW EXCLUSIVE MODE"
                )
                cursor.execute(sql, params)
                row = cursor.fetchone()
                if row is None:
                    raise HTTPException(
                        status_code=404, detail="Usuário não encontrado."
                    )
                return self._entity(row)
            finally:
                self._close_cursor(cursor)

    def delete(self, item_id: str) -> None:
        """Impede exclusão física mesmo em chamadas diretas ao repositório."""
        raise HTTPException(
            status_code=410,
            detail="Exclusão física indisponível. Use a operação de desativação lógica.",
        )

    def deactivate_user(
        self,
        item_id: str,
        *,
        event: Any,
        audit_sink: Any,
    ) -> None:
        """Desativa preservando o registro e grava auditoria atomicamente."""
        from app.core.audit import AuditEvent

        if not isinstance(event, AuditEvent):
            raise TypeError("Somente AuditEvent pode acompanhar a desativação.")
        if (
            event.action != "usuarios:desativar"
            or event.entity_type != "usuario"
            or event.entity_id != item_id
            or event.outcome != "success"
        ):
            raise ValueError("O evento de auditoria não corresponde à desativação.")
        if not callable(getattr(audit_sink, "append_in_transaction", None)):
            raise TypeError("audit_sink deve aceitar append_in_transaction.")

        with self._uow as uow:
            connection = uow.connection
            if connection is None:
                raise RuntimeError("A conexão PostgreSQL não foi aberta.")
            cursor = connection.cursor()
            try:
                cursor.execute(
                    f"LOCK TABLE {self._table} IN SHARE ROW EXCLUSIVE MODE"
                )
                cursor.execute(
                    f"SELECT perfil, status FROM {self._table} WHERE id = %s FOR UPDATE",
                    (item_id,),
                )
                current = cursor.fetchone()
                if current is None:
                    raise HTTPException(status_code=404, detail="Usuário não encontrado.")
                perfil, current_status = current
                if perfil not in ("Admin", "Operador") or current_status not in ("Ativo", "Inativo"):
                    raise HTTPException(
                        status_code=409,
                        detail="Estado cadastral inválido; desativação bloqueada.",
                    )
                if current_status == "Inativo":
                    return
                if perfil == "Admin":
                    cursor.execute(
                        f"SELECT count(*) FROM {self._table} "
                        "WHERE perfil = 'Admin' AND status = 'Ativo'"
                    )
                    count_row = cursor.fetchone()
                    active_admins = int(count_row[0]) if count_row else 0
                    if active_admins <= 1:
                        raise HTTPException(
                            status_code=409,
                            detail="Não é permitido desativar o último Admin ativo.",
                        )
                cursor.execute(
                    f"UPDATE {self._table} SET status = 'Inativo', "
                    "updated_at = now(), version = version + 1 WHERE id = %s",
                    (item_id,),
                )
                if not cursor.rowcount:
                    raise HTTPException(status_code=404, detail="Usuário não encontrado.")
                audit_sink.append_in_transaction(connection, event)
            finally:
                self._close_cursor(cursor)

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
                    self._close_cursor(cursor)
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
