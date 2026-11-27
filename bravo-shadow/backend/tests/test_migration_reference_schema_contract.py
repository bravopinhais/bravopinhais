"""Static alignment between confirmed legacy references and Shadow SQL FKs."""
from pathlib import Path

from app.core.migration_reference_reconciliation import CONFIRMED_REFERENCE_RULES


def test_confirmed_legacy_reference_rules_are_explicit_and_exact():
    actual = {
        (rule.key, rule.source_collection, rule.source_field,
         rule.target_collection, rule.target_field, rule.optional)
        for rule in CONFIRMED_REFERENCE_RULES
    }
    assert actual == {
        ("financeiro_plano_contas", "financeiro", "planoContaId",
         "plano_contas", "id", True),
        ("acertos_estoque_produtos", "acertos_estoque", "produtoId",
         "estoque", "id", False),
    }


def test_confirmed_reference_targets_have_matching_sql_primary_keys_and_foreign_keys():
    root = Path(__file__).resolve().parents[2]
    sql = (root / "docs" / "sql-piloto-financeiro.sql").read_text(encoding="utf-8")
    compact = " ".join(sql.split()).lower()
    assert "references bravo_shadow.plano_contas (id)" in compact
    assert "references bravo_shadow.estoque (id)" in compact
    assert "constraint financeiro_plano_conta_fk" in compact
    assert "constraint acertos_estoque_produto_fk" in compact


def test_target_only_optional_relationships_are_not_misrepresented_as_legacy_fields():
    root = Path(__file__).resolve().parents[2]
    sql = (root / "docs" / "sql-piloto-financeiro.sql").read_text(encoding="utf-8")
    compact = " ".join(sql.split()).lower()
    assert "references bravo_shadow.categorias (id)" in compact
    assert "references bravo_shadow.motivos_acerto (id)" in compact
    # No confirmed legacy reference rule currently claims these target-only links.
    keys = {rule.key for rule in CONFIRMED_REFERENCE_RULES}
    assert "documentos_categoria" not in keys
    assert "acertos_estoque_motivo" not in keys


def test_every_declared_sql_foreign_key_has_expected_column_target_and_delete_policy():
    root = Path(__file__).resolve().parents[2]
    sql = (root / "docs" / "sql-piloto-financeiro.sql").read_text(encoding="utf-8")
    compact = " ".join(sql.split()).lower()
    expected = {
        "financeiro_plano_conta_fk": (
            "foreign key (plano_conta_id) references bravo_shadow.plano_contas (id) on delete restrict",
        ),
        "documentos_categoria_fk": (
            "foreign key (categoria_id) references bravo_shadow.categorias (id) on delete restrict",
        ),
        "acertos_estoque_produto_fk": (
            "foreign key (produto_id) references bravo_shadow.estoque (id) on delete restrict",
        ),
        "acertos_estoque_motivo_fk": (
            "foreign key (motivo_id) references bravo_shadow.motivos_acerto (id) on delete restrict",
        ),
    }
    for constraint, fragments in expected.items():
        assert f"constraint {constraint}" in compact
        for fragment in fragments:
            assert fragment in compact

    # The target DDL permits null only on the two optional reference columns.
    assert "plano_conta_id text null" in compact
    assert "categoria_id text null" in compact
    assert "motivo_id text null" in compact
    assert "produto_id text not null" in compact


def test_confirmed_legacy_reference_rules_map_to_real_source_payload_fields():
    # The legacy adapter currently exposes camelCase source fields; target SQL
    # uses snake_case columns. Keep that mapping explicit and reviewable.
    mapping = {
        ("financeiro", "planoContaId"): ("financeiro", "plano_conta_id"),
        ("acertos_estoque", "produtoId"): ("acertos_estoque", "produto_id"),
    }
    actual = {
        (rule.source_collection, rule.source_field):
            (rule.target_collection, rule.target_field, rule.optional)
        for rule in CONFIRMED_REFERENCE_RULES
    }
    assert actual == {
        ("financeiro", "planoContaId"): ("plano_contas", "id", True),
        ("acertos_estoque", "produtoId"): ("estoque", "id", False),
    }
    assert set(actual) == set(mapping)
    assert all(
        source_collection and source_field and target_collection and target_column
        for (source_collection, source_field), (target_collection, target_column)
        in mapping.items()
    )
