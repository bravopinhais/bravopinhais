"""Contract checks for required destination fields in the PostgreSQL adapter.

These tests use no database connection and do not execute SQL.
"""
from __future__ import annotations

import pytest

from app.core.migration_apply_store_postgres import (
    REQUIRED_TARGET_COLUMNS,
    TARGET_COLUMNS,
    MigrationApplyStorePostgres,
)


class NoConnection:
    def cursor(self):
        raise AssertionError("validation must happen before SQL access")


def test_required_columns_are_a_subset_of_the_target_allowlist():
    for collection, required in REQUIRED_TARGET_COLUMNS.items():
        assert collection in TARGET_COLUMNS
        assert set(required) <= set(TARGET_COLUMNS[collection])


@pytest.mark.parametrize(
    ("collection", "payload"),
    [
        ("formas_monetarias", {}),
        ("plano_contas", {"codigo": "1", "nome": "Caixa"}),
        ("financeiro", {"tipo": "Pagar", "historico": "Conta"}),
        ("moradores", {"bloco": "A", "apartamento": "1"}),
        ("fornecedores", {"cnpj": "00",}),
        ("empregados", {"nome": "Pessoa"}),
        ("contas_bancarias", {}),
        ("conselheiros", {"nome": "Pessoa"}),
        ("usuarios", {"email": "a@b.com", "nome": "Pessoa"}),
        ("estoque", {}),
        ("categorias", {}),
        ("motivos_acerto", {}),
        ("documentos", {"titulo": "Doc", "nome_arquivo": "a.pdf"}),
        ("acertos_estoque", {"data": "2026-01-01", "tipo": "Entrada"}),
    ],
)
def test_insert_rejects_missing_required_fields_before_sql(collection, payload):
    with pytest.raises(ValueError, match="campos obrigatórios"):
        MigrationApplyStorePostgres().insert_target(
            NoConnection(), collection, "synthetic-destination-id", payload
        )


def test_condominio_allows_defaulted_fields_to_be_omitted():
    assert REQUIRED_TARGET_COLUMNS["condominio"] == ()

@pytest.mark.parametrize(("collection", "payload"), [
    ("formas_monetarias", {"nome": "   "}),
    ("plano_contas", {"codigo": "1", "nome": "", "tipo": "Receita"}),
    ("financeiro", {"tipo": "Pagar", "historico": "  ", "valor": "10.00"}),
    ("moradores", {"bloco": "A", "apartamento": "1", "nome": " "}),
    ("fornecedores", {"cnpj": "", "razao_social": "Empresa"}),
    ("empregados", {"nome": "Pessoa", "cargo": " "}),
    ("contas_bancarias", {"banco": " "}),
    ("conselheiros", {"nome": "Pessoa", "cargo": ""}),
    ("usuarios", {"email": " ", "nome": "Pessoa", "cargo": "Admin"}),
    ("estoque", {"item": ""}),
    ("categorias", {"nome": " "}),
    ("motivos_acerto", {"nome": ""}),
    ("documentos", {"titulo": "Doc", "nome_arquivo": "a.pdf", "arquivo_compactado_gzip": " "}),
    ("acertos_estoque", {"data": "2026-01-01T00:00:00Z", "tipo": "Entrada", "produto_id": "p1", "quantidade": "1.000", "motivo": " "}),
])
def test_insert_rejects_blank_required_text_before_sql(collection, payload):
    with pytest.raises(ValueError, match="campos textuais obrigatórios vazios"):
        MigrationApplyStorePostgres().insert_target(
            NoConnection(), collection, "synthetic-destination-id", payload
        )

def test_defaulted_fields_are_not_injected_by_adapter_when_omitted():
    # SQL owns defaults; the adapter only inserts explicitly supplied columns.
    assert "quantidade" not in REQUIRED_TARGET_COLUMNS["estoque"]
    assert "saldo" not in REQUIRED_TARGET_COLUMNS["contas_bancarias"]
    assert "perfil" not in REQUIRED_TARGET_COLUMNS["usuarios"]
    assert "status" not in REQUIRED_TARGET_COLUMNS["usuarios"]
