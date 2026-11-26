from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from typing import Any

from fastapi import HTTPException

from app.core.postgres import PostgresUnitOfWork
from app.modules.contas_bancarias.schemas import ContaBancaria
from app.modules.empregados.schemas import Empregado
from app.modules.fornecedores.schemas import Fornecedor
from app.modules.moradores.schemas import Morador


class _PostgresCadastroRepository:
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

    @staticmethod
    def _missing(detail: str) -> HTTPException:
        return HTTPException(status_code=404, detail=detail)


class PostgresMoradoresRepository(_PostgresCadastroRepository):
    _table = "bravo_shadow.moradores"
    _columns = (
        "id, bloco, apartamento, nome, email, telefone, cpf, pet_nome, vaga_garagem"
    )

    @staticmethod
    def _entity(row) -> Morador | None:
        if row is None:
            return None
        return Morador(
            id=row[0], bloco=row[1], apartamento=row[2], nome=row[3],
            email=row[4], telefone=row[5], cpf=row[6], petNome=row[7],
            vagaGaragem=row[8],
        )

    @staticmethod
    def _values(item: Morador) -> tuple[Any, ...]:
        return (
            item.bloco, item.apartamento, item.nome, item.email, item.telefone,
            item.cpf, item.petNome, item.vagaGaragem,
        )

    def list(self) -> list[Morador]:
        rows = self._query(
            f"SELECT {self._columns} FROM {self._table} ORDER BY bloco, apartamento, nome, id",
            fetch="all",
        )
        return [self._entity(row) for row in rows]

    def get(self, item_id: str) -> Morador | None:
        return self._entity(self._query(
            f"SELECT {self._columns} FROM {self._table} WHERE id = %s",
            (item_id,), fetch="one",
        ))

    def exists(self, item_id: str) -> bool:
        return self.get(item_id) is not None

    def add(self, item_id: str, item: Morador) -> None:
        self._query(
            f"INSERT INTO {self._table} "
            "(id, bloco, apartamento, nome, email, telefone, cpf, pet_nome, vaga_garagem) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (item_id, *self._values(item)),
        )

    def replace(self, item_id: str, item: Morador) -> None:
        changed = self._query(
            f"UPDATE {self._table} SET bloco = %s, apartamento = %s, nome = %s, "
            "email = %s, telefone = %s, cpf = %s, pet_nome = %s, vaga_garagem = %s, "
            "updated_at = now(), version = version + 1 WHERE id = %s",
            (*self._values(item), item_id),
        )
        if not changed:
            raise self._missing("Morador não encontrado.")

    def delete(self, item_id: str) -> None:
        changed = self._query(f"DELETE FROM {self._table} WHERE id = %s", (item_id,))
        if not changed:
            raise self._missing("Morador não encontrado.")


class PostgresFornecedoresRepository(_PostgresCadastroRepository):
    _table = "bravo_shadow.fornecedores"
    _columns = "id, cnpj, razao_social"

    @staticmethod
    def _entity(row) -> Fornecedor | None:
        return Fornecedor(id=row[0], cnpj=row[1], razaoSocial=row[2]) if row else None

    def list(self) -> list[Fornecedor]:
        rows = self._query(
            f"SELECT {self._columns} FROM {self._table} ORDER BY razao_social, id",
            fetch="all",
        )
        return [self._entity(row) for row in rows]

    def get(self, item_id: str) -> Fornecedor | None:
        return self._entity(self._query(
            f"SELECT {self._columns} FROM {self._table} WHERE id = %s",
            (item_id,), fetch="one",
        ))

    def exists(self, item_id: str) -> bool:
        return self.get(item_id) is not None

    def add(self, item_id: str, item: Fornecedor) -> None:
        self._query(
            f"INSERT INTO {self._table} (id, cnpj, razao_social) VALUES (%s, %s, %s)",
            (item_id, item.cnpj, item.razaoSocial),
        )

    def replace(self, item_id: str, item: Fornecedor) -> None:
        changed = self._query(
            f"UPDATE {self._table} SET cnpj = %s, razao_social = %s, "
            "updated_at = now(), version = version + 1 WHERE id = %s",
            (item.cnpj, item.razaoSocial, item_id),
        )
        if not changed:
            raise self._missing("Fornecedor não encontrado.")

    def delete(self, item_id: str) -> None:
        changed = self._query(f"DELETE FROM {self._table} WHERE id = %s", (item_id,))
        if not changed:
            raise self._missing("Fornecedor não encontrado.")


class PostgresEmpregadosRepository(_PostgresCadastroRepository):
    _table = "bravo_shadow.empregados"
    _columns = (
        "id, nome, cargo, empresa, endereco, telefone, contato_emergencia_nome, "
        "contato_emergencia_tel"
    )

    @staticmethod
    def _entity(row) -> Empregado | None:
        if row is None:
            return None
        return Empregado(
            id=row[0], nome=row[1], cargo=row[2], empresa=row[3],
            endereco=row[4], telefone=row[5],
            contatoEmergenciaNome=row[6], contatoEmergenciaTel=row[7],
        )

    @staticmethod
    def _values(item: Empregado) -> tuple[Any, ...]:
        return (
            item.nome, item.cargo, item.empresa, item.endereco, item.telefone,
            item.contatoEmergenciaNome, item.contatoEmergenciaTel,
        )

    def list(self) -> list[Empregado]:
        rows = self._query(
            f"SELECT {self._columns} FROM {self._table} ORDER BY nome, id",
            fetch="all",
        )
        return [self._entity(row) for row in rows]

    def get(self, item_id: str) -> Empregado | None:
        return self._entity(self._query(
            f"SELECT {self._columns} FROM {self._table} WHERE id = %s",
            (item_id,), fetch="one",
        ))

    def exists(self, item_id: str) -> bool:
        return self.get(item_id) is not None

    def add(self, item_id: str, item: Empregado) -> None:
        self._query(
            f"INSERT INTO {self._table} "
            "(id, nome, cargo, empresa, endereco, telefone, contato_emergencia_nome, "
            "contato_emergencia_tel) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (item_id, *self._values(item)),
        )

    def replace(self, item_id: str, item: Empregado) -> None:
        changed = self._query(
            f"UPDATE {self._table} SET nome = %s, cargo = %s, empresa = %s, "
            "endereco = %s, telefone = %s, contato_emergencia_nome = %s, "
            "contato_emergencia_tel = %s, updated_at = now(), version = version + 1 "
            "WHERE id = %s",
            (*self._values(item), item_id),
        )
        if not changed:
            raise self._missing("Empregado não encontrado.")

    def delete(self, item_id: str) -> None:
        changed = self._query(f"DELETE FROM {self._table} WHERE id = %s", (item_id,))
        if not changed:
            raise self._missing("Empregado não encontrado.")


class PostgresContasBancariasRepository(_PostgresCadastroRepository):
    _table = "bravo_shadow.contas_bancarias"
    _columns = "id, banco, saldo"

    @staticmethod
    def _entity(row) -> ContaBancaria | None:
        return ContaBancaria(id=row[0], banco=row[1], saldo=Decimal(row[2])) if row else None

    def list(self) -> list[ContaBancaria]:
        rows = self._query(
            f"SELECT {self._columns} FROM {self._table} ORDER BY banco, id",
            fetch="all",
        )
        return [self._entity(row) for row in rows]

    def get(self, item_id: str) -> ContaBancaria | None:
        return self._entity(self._query(
            f"SELECT {self._columns} FROM {self._table} WHERE id = %s",
            (item_id,), fetch="one",
        ))

    def exists(self, item_id: str) -> bool:
        return self.get(item_id) is not None

    def add(self, item_id: str, item: ContaBancaria) -> None:
        self._query(
            f"INSERT INTO {self._table} (id, banco, saldo) VALUES (%s, %s, %s)",
            (item_id, item.banco, item.saldo),
        )

    def replace(self, item_id: str, item: ContaBancaria) -> None:
        changed = self._query(
            f"UPDATE {self._table} SET banco = %s, saldo = %s, "
            "updated_at = now(), version = version + 1 WHERE id = %s",
            (item.banco, item.saldo, item_id),
        )
        if not changed:
            raise self._missing("Conta bancária não encontrada.")

    def delete(self, item_id: str) -> None:
        changed = self._query(f"DELETE FROM {self._table} WHERE id = %s", (item_id,))
        if not changed:
            raise self._missing("Conta bancária não encontrada.")
