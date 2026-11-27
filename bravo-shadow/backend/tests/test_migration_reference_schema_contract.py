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
