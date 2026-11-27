"""Integração real de movimentos de estoque (PostgreSQL descartável)."""
from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from urllib.parse import urlparse
from uuid import uuid4

import psycopg
import pytest
from fastapi import HTTPException

from app.core.postgres_inventory import PostgresAcertosEstoqueRepository
from app.modules.acertos_estoque.schemas import Acerto
from app.core.postgres_inventory import PostgresEstoqueRepository
from app.modules.estoque.schemas import EstoqueItem


DATABASE_URL = os.getenv("BRAVO_SHADOW_TEST_DATABASE_URL")


def _guard_test_database(url: str) -> None:
    if os.getenv("BRAVO_SHADOW_ALLOW_DESTRUCTIVE_TEST_DATABASE") != "1":
        raise RuntimeError(
            "Integração destrutiva bloqueada: defina "
            "BRAVO_SHADOW_ALLOW_DESTRUCTIVE_TEST_DATABASE=1 apenas para "
            "o banco descartável dedicado."
        )
    parsed = urlparse(url)
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise RuntimeError("A URL de integração precisa usar PostgreSQL.")
    if parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError("Os testes só podem conectar a PostgreSQL local/descartável.")
    if parsed.path.lstrip("/") != "bravo_shadow_test":
        raise RuntimeError(
            "BRAVO_SHADOW_TEST_DATABASE_URL precisa apontar exatamente para "
            "o banco descartável bravo_shadow_test."
        )


@pytest.fixture
def postgres_inventory_database():
    if not DATABASE_URL:
        pytest.skip("PostgreSQL real não configurado; integração opt-in.")

    _guard_test_database(DATABASE_URL)
    ddl = Path(__file__).resolve().parents[2] / "docs" / "sql-piloto-financeiro.sql"

    # Os papéis padrão só são preparados dentro do banco local descartável,
    # para que os REVOKE do rascunho SQL possam ser avaliados.
    with psycopg.connect(DATABASE_URL, autocommit=True) as connection:
        for role in ("anon", "authenticated", "service_role"):
            exists = connection.execute(
                "SELECT 1 FROM pg_roles WHERE rolname = %s", (role,)
            ).fetchone()
            if exists is None:
                connection.execute(f'CREATE ROLE "{role}" NOLOGIN')
        connection.execute("DROP SCHEMA IF EXISTS bravo_shadow CASCADE")
        connection.execute(ddl.read_text(encoding="utf-8"), prepare=False)

    try:
        yield DATABASE_URL
    finally:
        with psycopg.connect(DATABASE_URL, autocommit=True) as connection:
            connection.execute("DROP SCHEMA IF EXISTS bravo_shadow CASCADE")


def _repository(database_url: str) -> PostgresAcertosEstoqueRepository:
    return PostgresAcertosEstoqueRepository(lambda: psycopg.connect(database_url))


def _insert_product(database_url: str, product_id: str, quantity: int) -> None:
    with psycopg.connect(database_url) as connection:
        connection.execute(
            """
            INSERT INTO bravo_shadow.estoque (id, item, quantidade, minimo, maximo)
            VALUES (%s, %s, %s, 0, 100)
            """,
            (product_id, "Item sintético de integração", quantity),
        )


def _movement(product_id: str, movement_id: str, quantity: int) -> Acerto:
    return Acerto(
        id=movement_id,
        data="2026-11-27T12:00:00-03:00",
        tipo="Saída",
        produtoId=product_id,
        quantidade=quantity,
        motivo="Teste sintético de concorrência",
    )


def test_real_postgres_rolls_back_balance_when_history_insert_fails(postgres_inventory_database):
    database_url = postgres_inventory_database
    product_id = f"stock-{uuid4().hex}"
    _insert_product(database_url, product_id, 10)

    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute(
            """
            CREATE FUNCTION bravo_shadow.reject_stock_history() RETURNS trigger
            LANGUAGE plpgsql AS $$
            BEGIN
                RAISE EXCEPTION 'forced stock history failure';
            END;
            $$
            """
        )
        connection.execute(
            f"""
            CREATE TRIGGER reject_stock_history_{uuid4().hex[:12]}
            BEFORE INSERT ON bravo_shadow.acertos_estoque
            FOR EACH ROW EXECUTE FUNCTION bravo_shadow.reject_stock_history()
            """
        )
        trigger_name = connection.execute(
            """
            SELECT tgname FROM pg_trigger
            WHERE tgrelid = 'bravo_shadow.acertos_estoque'::regclass
              AND NOT tgisinternal
            ORDER BY oid DESC LIMIT 1
            """
        ).fetchone()[0]

    try:
        with pytest.raises(psycopg.Error, match="forced stock history failure"):
            _repository(database_url).register_movement(
                product_id=product_id,
                movement=_movement(product_id, f"movement-{uuid4().hex}", 3),
                delta=-3,
            )

        with psycopg.connect(database_url) as connection:
            balance = connection.execute(
                "SELECT quantidade FROM bravo_shadow.estoque WHERE id = %s",
                (product_id,),
            ).fetchone()[0]
            history_count = connection.execute(
                "SELECT count(*) FROM bravo_shadow.acertos_estoque WHERE produto_id = %s",
                (product_id,),
            ).fetchone()[0]

        assert balance == 10
        assert history_count == 0
    finally:
        with psycopg.connect(database_url, autocommit=True) as connection:
            connection.execute(
                f'DROP TRIGGER IF EXISTS "{trigger_name}" ON bravo_shadow.acertos_estoque'
            )
            connection.execute(
                "DROP FUNCTION IF EXISTS bravo_shadow.reject_stock_history()"
            )


def test_real_postgres_serializes_concurrent_stock_exits_without_negative_balance(
    postgres_inventory_database,
):
    database_url = postgres_inventory_database
    product_id = f"stock-{uuid4().hex}"
    _insert_product(database_url, product_id, 5)
    barrier = Barrier(2)

    def withdraw(index: int) -> str:
        movement = _movement(product_id, f"movement-{uuid4().hex}", 4)
        barrier.wait(timeout=10)
        try:
            _repository(database_url).register_movement(
                product_id=product_id,
                movement=movement,
                delta=-4,
            )
            return "committed"
        except HTTPException as error:
            if error.status_code != 409:
                raise
            return "insufficient_stock"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(withdraw, (1, 2)))

    assert outcomes.count("committed") == 1
    assert outcomes.count("insufficient_stock") == 1

    with psycopg.connect(database_url) as connection:
        balance = connection.execute(
            "SELECT quantidade FROM bravo_shadow.estoque WHERE id = %s",
            (product_id,),
        ).fetchone()[0]
        history = connection.execute(
            """
            SELECT count(*), coalesce(sum(quantidade), 0)
            FROM bravo_shadow.acertos_estoque
            WHERE produto_id = %s AND tipo = 'Saída'
            """,
            (product_id,),
        ).fetchone()

    assert balance == 1
    assert history == (1, 4)



def test_real_postgres_serializes_product_edit_with_movement(postgres_inventory_database):
    database_url = postgres_inventory_database
    product_id = f"stock-{uuid4().hex}"
    _insert_product(database_url, product_id, 5)
    barrier = Barrier(2)

    edited_item = EstoqueItem(
        id=product_id,
        item="Produto sintético editado",
        quantidade=8,
        minimo=0,
        maximo=100,
        etiqueta="",
        fotoNome="",
        fotoCompactadaGzip="",
        marca="Marca teste",
        linha="Linha teste",
        fabricante="Fabricante teste",
        dataCadastro="",
    )

    def edit_product() -> str:
        barrier.wait(timeout=10)
        try:
            PostgresEstoqueRepository(
                lambda: psycopg.connect(database_url)
            ).replace(product_id, edited_item)
            return "edited"
        except HTTPException as error:
            if error.status_code != 409:
                raise
            return "edit_rejected_after_movement"

    def register_movement() -> str:
        barrier.wait(timeout=10)
        movement = _movement(product_id, f"movement-{uuid4().hex}", 2)
        PostgresAcertosEstoqueRepository(
            lambda: psycopg.connect(database_url)
        ).register_movement(
            product_id=product_id,
            movement=movement,
            delta=-2,
        )
        return "movement_committed"

    with ThreadPoolExecutor(max_workers=2) as pool:
        edit_future = pool.submit(edit_product)
        movement_future = pool.submit(register_movement)
        edit_outcome = edit_future.result(timeout=20)
        movement_outcome = movement_future.result(timeout=20)

    assert movement_outcome == "movement_committed"
    assert edit_outcome in {"edited", "edit_rejected_after_movement"}

    with psycopg.connect(database_url) as connection:
        product = connection.execute(
            "SELECT quantidade, item, marca FROM bravo_shadow.estoque WHERE id = %s",
            (product_id,),
        ).fetchone()
        history = connection.execute(
            "SELECT count(*), coalesce(sum(quantidade), 0) "
            "FROM bravo_shadow.acertos_estoque WHERE produto_id = %s",
            (product_id,),
        ).fetchone()

    assert history == (1, 2)
    if edit_outcome == "edited":
        assert product == (6, "Produto sintético editado", "Marca teste")
    else:
        assert product == (3, "Item sintético de integração", "")


@pytest.mark.parametrize(
    "relationship",
    ["document_category", "stock_product", "stock_reason", "financial_account"],
)
def test_real_postgres_restricts_deletion_of_referenced_parent(
    postgres_inventory_database, relationship
):
    """FK RESTRICT deve bloquear exclusão e preservar pai e filho."""
    database_url = postgres_inventory_database
    suffix = uuid4().hex
    parent_id = f"parent-{suffix}"
    child_id = f"child-{suffix}"

    with psycopg.connect(database_url) as connection:
        if relationship == "document_category":
            connection.execute(
                "INSERT INTO bravo_shadow.categorias (id, nome) VALUES (%s, %s)",
                (parent_id, "Categoria sintética"),
            )
            connection.execute(
                """
                INSERT INTO bravo_shadow.documentos
                    (id, titulo, nome_arquivo, arquivo_compactado_gzip, categoria_id)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (child_id, "Documento sintético", "teste.txt", "conteudo-sintetico", parent_id),
            )
            delete_sql = "DELETE FROM bravo_shadow.categorias WHERE id = %s"
            parent_table, child_table = "categorias", "documentos"
            child_fk = "categoria_id"
        elif relationship == "stock_product":
            _insert_product(database_url, parent_id, 7)
            connection.execute(
                """
                INSERT INTO bravo_shadow.acertos_estoque
                    (id, data, tipo, produto_id, quantidade, motivo)
                VALUES (%s, now(), 'Saída', %s, 1, %s)
                """,
                (child_id, parent_id, "Motivo sintético"),
            )
            delete_sql = "DELETE FROM bravo_shadow.estoque WHERE id = %s"
            parent_table, child_table = "estoque", "acertos_estoque"
            child_fk = "produto_id"
        elif relationship == "stock_reason":
            connection.execute(
                "INSERT INTO bravo_shadow.motivos_acerto (id, nome) VALUES (%s, %s)",
                (parent_id, "Motivo sintético"),
            )
            _insert_product(database_url, f"product-{suffix}", 7)
            connection.execute(
                """
                INSERT INTO bravo_shadow.acertos_estoque
                    (id, data, tipo, produto_id, quantidade, motivo, motivo_id)
                VALUES (%s, now(), 'Saída', %s, 1, %s, %s)
                """,
                (child_id, f"product-{suffix}", "Motivo sintético", parent_id),
            )
            delete_sql = "DELETE FROM bravo_shadow.motivos_acerto WHERE id = %s"
            parent_table, child_table = "motivos_acerto", "acertos_estoque"
            child_fk = "motivo_id"
        else:
            connection.execute(
                """
                INSERT INTO bravo_shadow.plano_contas (id, codigo, nome, tipo)
                VALUES (%s, %s, %s, 'Despesa')
                """,
                (parent_id, f"TEST-{suffix}", "Conta sintética"),
            )
            connection.execute(
                """
                INSERT INTO bravo_shadow.financeiro
                    (id, tipo, plano_conta_id, historico, valor)
                VALUES (%s, 'Pagar', %s, %s, 10.00)
                """,
                (child_id, parent_id, "Lançamento sintético"),
            )
            delete_sql = "DELETE FROM bravo_shadow.plano_contas WHERE id = %s"
            parent_table, child_table = "plano_contas", "financeiro"
            child_fk = "plano_conta_id"

        with pytest.raises(psycopg.errors.ForeignKeyViolation) as error:
            connection.execute(delete_sql, (parent_id,))
        assert error.value.sqlstate == "23503"
        connection.rollback()

    with psycopg.connect(database_url) as connection:
        parent_count = connection.execute(
            f"SELECT count(*) FROM bravo_shadow.{parent_table} WHERE id = %s",
            (parent_id,),
        ).fetchone()[0]
        child_count = connection.execute(
            f"SELECT count(*) FROM bravo_shadow.{child_table} WHERE id = %s AND {child_fk} = %s",
            (child_id, parent_id),
        ).fetchone()[0]

    assert parent_count == 1
    assert child_count == 1
