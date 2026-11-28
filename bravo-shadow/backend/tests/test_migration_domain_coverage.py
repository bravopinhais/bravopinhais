from app.core.migration_domain_coverage import DOMAIN_COVERAGE, domain_coverage_by_key


def test_coverage_register_accounts_for_all_sixteen_legacy_domains_once():
    keys = [item.legacy_key for item in DOMAIN_COVERAGE]
    assert len(keys) == 16
    assert len(set(keys)) == 16
    assert set(keys) == {
        "condominio", "conselheiros", "usuarios", "plano_contas",
        "financeiro", "formas_monetarias", "contas_bancarias", "moradores",
        "fornecedores", "empregados", "categorias", "estoque",
        "acertos_estoque", "motivos_acerto_estoque", "documentos", "logs",
    }


def test_domains_without_field_allowlists_remain_explicitly_blocked():
    lookup = domain_coverage_by_key()
    blocked = {
        "conselheiros", "formas_monetarias", "contas_bancarias",
        "moradores", "fornecedores", "empregados", "categorias", "logs",
    }
    assert all(lookup[key].status == "blocked_no_field_allowlist" for key in blocked)


def test_contract_presence_does_not_claim_import_readiness():
    lookup = domain_coverage_by_key()
    assert lookup["condominio"].status == "manual_source_locator_required"
    assert lookup["financeiro"].status == "review_only"
    assert lookup["usuarios"].status == "review_only"
    assert lookup["plano_contas"].status == "review_only"
    assert lookup["documentos"].status == "review_only"
