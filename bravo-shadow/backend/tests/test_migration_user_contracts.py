from app.core.migration_source_inventory import inspect_source_collections
from app.core.migration_user_contracts import assess_legacy_users


def _user(**overrides):
    record = {
        "id": "usr-synthetic", "usuario": "operador", "nome": "Pessoa Sintética",
        "email": "sintetico@example.invalid", "cargo": "Operador",
        "loja": "Condomínio Sintético", "perfil": "Operador",
        "status": "Ativo", "primeiroAcesso": True,
    }
    record.update(overrides)
    return record


def test_user_contract_assesses_only_confirmed_noncredential_fields():
    result = assess_legacy_users(inspect_source_collections({"usuarios": [_user()]}))
    assert result.status == "review_required"
    assert result.missing_required == ()
    assert result.forbidden_fields == ()
    assert result.unexpected_fields == ()


def test_user_contract_detects_and_excludes_legacy_password_field():
    result = assess_legacy_users(inspect_source_collections({
        "usuarios": [_user(senhaHash="SENHA-SINTETICA-NAO-REPRODUZIR")]
    }))
    assert result.forbidden_fields == ("senhaHash",)
    assert "senhaHash" not in result.unexpected_fields
    assert "SENHA-SINTETICA-NAO-REPRODUZIR" not in repr(result)


def test_user_contract_flags_unknown_fields_partial_fields_and_wrong_types():
    result = assess_legacy_users(inspect_source_collections({
        "usuarios": [
            _user(email=None, campoNovo="valor-sintetico"),
            _user(),
        ]
    }))
    assert "email" in result.type_mismatches
    assert "campoNovo" in result.unexpected_fields
    assert "email" not in result.partially_populated  # null is present; type mismatch is reported
    assert result.status == "review_required"
