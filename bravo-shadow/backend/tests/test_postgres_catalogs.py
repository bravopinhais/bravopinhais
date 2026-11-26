from fastapi import HTTPException
import pytest

from app.core.postgres_catalogs import (
    PostgresCategoriasRepository,
    PostgresDocumentosRepository,
    PostgresMotivosAcertoRepository,
)
from app.modules.categorias.schemas import Categoria
from app.modules.documentos.schemas import Documento
from app.modules.motivos_acerto.schemas import MotivoAcerto


class ForeignKeyError(Exception):
    sqlstate = "23503"


class Cursor:
    def __init__(self, connection):
        self.connection = connection
        self.rowcount = 1

    def execute(self, sql, params=()):
        self.connection.calls.append((sql, params))
        if self.connection.error is not None:
            raise self.connection.error
        if sql.lstrip().startswith("SELECT"):
            self.connection.row = self.connection.row_value
        self.rowcount = self.connection.rowcount

    def fetchone(self):
        return self.connection.row

    def fetchall(self):
        return self.connection.rows

    def close(self):
        self.connection.cursor_closed += 1


class Connection:
    def __init__(self, *, row=None, rows=None, error=None, rowcount=1):
        self.row_value = row
        self.row = None
        self.rows = rows or []
        self.error = error
        self.rowcount = rowcount
        self.calls = []
        self.commits = 0
        self.rollbacks = 0
        self.closed = 0
        self.cursor_closed = 0

    def cursor(self):
        return Cursor(self)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed += 1


def factory(connection):
    return lambda: connection


def test_categories_repository_maps_and_inserts_catalog_entries():
    connection = Connection(row=("cat_1", "Manutenção"))
    repository = PostgresCategoriasRepository(factory(connection))

    assert repository.get("cat_1") == Categoria(id="cat_1", nome="Manutenção")
    repository.add("cat_2", Categoria(id="cat_2", nome="Financeiro"))

    assert "bravo_shadow.categorias" in connection.calls[0][0]
    assert connection.calls[1][1] == ("cat_2", "Financeiro")
    assert connection.commits == 2
    assert connection.closed == 2


def test_reason_delete_translates_foreign_key_to_conflict():
    connection = Connection(error=ForeignKeyError("referenced"))
    repository = PostgresMotivosAcertoRepository(factory(connection))

    with pytest.raises(HTTPException) as error:
        repository.delete("mot_1")

    assert error.value.status_code == 409
    assert "motivos_acerto" in connection.calls[0][0]
    assert connection.rollbacks == 1
    assert connection.commits == 0


def test_document_repository_preserves_category_and_compressed_file():
    connection = Connection()
    repository = PostgresDocumentosRepository(factory(connection))
    document = Documento(
        id="doc_1", pasta="Financeiro", categoriaId="cat_1",
        titulo="Nota fiscal", nomeArquivo="nota.pdf",
        arquivoCompactadoGzip="H4sIAAAAA",
    )

    repository.add(document.id, document)

    sql, params = connection.calls[0]
    assert "bravo_shadow.documentos" in sql
    assert params == (
        "doc_1", "Financeiro", "cat_1", "Nota fiscal", "nota.pdf", "H4sIAAAAA",
    )
    assert connection.commits == 1
    assert connection.closed == 1


def test_document_repository_maps_nullable_category():
    connection = Connection(row=(
        "doc_2", "Geral", None, "Contrato", "contrato.pdf", "gzip-data",
    ))
    repository = PostgresDocumentosRepository(factory(connection))

    document = repository.get("doc_2")

    assert document.categoriaId is None
    assert document.pasta == "Geral"
    assert document.arquivoCompactadoGzip == "gzip-data"


def test_category_delete_translates_document_reference_to_conflict():
    connection = Connection(error=ForeignKeyError("referenced"))
    repository = PostgresCategoriasRepository(factory(connection))

    with pytest.raises(HTTPException) as error:
        repository.delete("cat_1")

    assert error.value.status_code == 409
    assert connection.rollbacks == 1
