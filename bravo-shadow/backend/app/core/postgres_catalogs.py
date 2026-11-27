from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import HTTPException

from app.core.postgres import PostgresUnitOfWork
from app.modules.categorias.schemas import Categoria
from app.modules.documentos.schemas import Documento, DocumentoResumo
from app.modules.motivos_acerto.schemas import MotivoAcerto


class _CatalogRepository:
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

    def _delete(self, table: str, item_id: str, missing_detail: str, reference_detail: str) -> None:
        try:
            changed = self._query(f"DELETE FROM {table} WHERE id = %s", (item_id,))
        except Exception as exc:
            if self._sqlstate(exc) == "23503":
                raise HTTPException(status_code=409, detail=reference_detail) from exc
            raise
        if not changed:
            raise HTTPException(status_code=404, detail=missing_detail)


class PostgresCategoriasRepository(_CatalogRepository):
    _table = "bravo_shadow.categorias"

    @staticmethod
    def _entity(row) -> Categoria | None:
        return Categoria(id=row[0], nome=row[1]) if row else None

    def list(self) -> list[Categoria]:
        rows = self._query(
            f"SELECT id, nome FROM {self._table} ORDER BY nome, id",
            fetch="all",
        )
        return [self._entity(row) for row in rows]

    def get(self, item_id: str) -> Categoria | None:
        return self._entity(self._query(
            f"SELECT id, nome FROM {self._table} WHERE id = %s",
            (item_id,), fetch="one",
        ))

    def exists(self, item_id: str) -> bool:
        return self.get(item_id) is not None

    def add(self, item_id: str, item: Categoria) -> None:
        self._query(
            f"INSERT INTO {self._table} (id, nome) VALUES (%s, %s)",
            (item_id, item.nome),
        )

    def replace(self, item_id: str, item: Categoria) -> None:
        changed = self._query(
            f"UPDATE {self._table} SET nome = %s, updated_at = now(), "
            f"version = version + 1 WHERE id = %s",
            (item.nome, item_id),
        )
        if not changed:
            raise HTTPException(status_code=404, detail="Pasta não encontrada.")

    def delete(self, item_id: str) -> None:
        self._delete(
            self._table, item_id, "Pasta não encontrada.",
            "Não é possível excluir uma categoria vinculada a documentos.",
        )


class PostgresMotivosAcertoRepository(_CatalogRepository):
    _table = "bravo_shadow.motivos_acerto"

    @staticmethod
    def _entity(row) -> MotivoAcerto | None:
        return MotivoAcerto(id=row[0], nome=row[1]) if row else None

    def list(self) -> list[MotivoAcerto]:
        rows = self._query(
            f"SELECT id, nome FROM {self._table} ORDER BY nome, id",
            fetch="all",
        )
        return [self._entity(row) for row in rows]

    def get(self, item_id: str) -> MotivoAcerto | None:
        return self._entity(self._query(
            f"SELECT id, nome FROM {self._table} WHERE id = %s",
            (item_id,), fetch="one",
        ))

    def exists(self, item_id: str) -> bool:
        return self.get(item_id) is not None

    def add(self, item_id: str, item: MotivoAcerto) -> None:
        self._query(
            f"INSERT INTO {self._table} (id, nome) VALUES (%s, %s)",
            (item_id, item.nome),
        )

    def replace(self, item_id: str, item: MotivoAcerto) -> None:
        changed = self._query(
            f"UPDATE {self._table} SET nome = %s, updated_at = now(), "
            f"version = version + 1 WHERE id = %s",
            (item.nome, item_id),
        )
        if not changed:
            raise HTTPException(status_code=404, detail="Motivo não encontrado.")

    def delete(self, item_id: str) -> None:
        self._delete(
            self._table, item_id, "Motivo não encontrado.",
            "Não é possível excluir um motivo utilizado em acertos de estoque.",
        )


class PostgresDocumentosRepository(_CatalogRepository):
    _table = "bravo_shadow.documentos"
    _columns = (
        "id, pasta, categoria_id, titulo, nome_arquivo, arquivo_compactado_gzip"
    )

    @staticmethod
    def _entity(row) -> Documento | None:
        if row is None:
            return None
        return Documento(
            id=row[0], pasta=row[1], categoriaId=row[2], titulo=row[3],
            nomeArquivo=row[4], arquivoCompactadoGzip=row[5],
        )

    @staticmethod
    def _values(item: Documento) -> tuple[Any, ...]:
        return (
            item.pasta, item.categoriaId, item.titulo,
            item.nomeArquivo, item.arquivoCompactadoGzip,
        )

    def list(self) -> list[Documento]:
        rows = self._query(
            f"SELECT {self._columns} FROM {self._table} ORDER BY created_at, id",
            fetch="all",
        )
        return [self._entity(row) for row in rows]

    def get(self, item_id: str) -> Documento | None:
        return self._entity(self._query(
            f"SELECT {self._columns} FROM {self._table} WHERE id = %s",
            (item_id,), fetch="one",
        ))

    def list_metadata(self) -> list[DocumentoResumo]:
        rows = self._query(
            f"SELECT id, pasta, categoria_id, titulo, nome_arquivo "
            f"FROM {self._table} ORDER BY created_at, id",
            fetch="all",
        )
        return [
            DocumentoResumo(
                id=row[0], pasta=row[1], categoriaId=row[2],
                titulo=row[3], nomeArquivo=row[4],
            )
            for row in rows
        ]

    def exists(self, item_id: str) -> bool:
        return self.get(item_id) is not None

    def add(self, item_id: str, item: Documento) -> None:
        try:
            self._query(
                f"INSERT INTO {self._table} "
                "(id, pasta, categoria_id, titulo, nome_arquivo, arquivo_compactado_gzip) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (item_id, *self._values(item)),
            )
        except Exception as exc:
            if self._sqlstate(exc) == "23503":
                raise HTTPException(status_code=409, detail="A categoria informada não existe.") from exc
            raise

    def replace(self, item_id: str, item: Documento) -> None:
        try:
            changed = self._query(
                f"UPDATE {self._table} SET pasta = %s, categoria_id = %s, "
                "titulo = %s, nome_arquivo = %s, arquivo_compactado_gzip = %s, "
                "updated_at = now(), version = version + 1 WHERE id = %s",
                (*self._values(item), item_id),
            )
        except Exception as exc:
            if self._sqlstate(exc) == "23503":
                raise HTTPException(status_code=409, detail="A categoria informada não existe.") from exc
            raise
        if not changed:
            raise HTTPException(status_code=404, detail="Documento não encontrado.")

    def delete(self, item_id: str) -> None:
        self._delete(
            self._table, item_id, "Documento não encontrado.",
            "Não é possível excluir o documento por causa de um vínculo ativo.",
        )
