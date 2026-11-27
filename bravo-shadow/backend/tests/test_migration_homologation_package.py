from dataclasses import replace

import pytest

from app.core.migration_integrated_preflight import run_integrated_migration_preflight
from app.core.migration_homologation_package import (
    build_synthetic_homologation_package,
    serialize_homologation_package,
    verify_homologation_package,
)

def build():
    preflight = run_integrated_migration_preflight({
        "financeiro": [{"id":"f1", "tipo":"Receber", "planoContaId":None,
                        "historico":"sintetico", "valor":12.34}],
        "plano_contas": [{"id":"pc1", "codigo":"1", "nome":"Receita", "tipo":"Receber"}],
        "estoque": [{"id":"p1", "item":"Item sintético", "quantidade":2}],
        "acertos_estoque": [{"id":"m1", "data":"27/11/2026", "tipo":"Entrada",
                             "produtoId":"p1", "quantidade":1, "motivo":"Teste"}],
        "documentos": [],
    })
    return build_synthetic_homologation_package(
        preflight, source_system="legacy-synthetic",
        source_baseline="baseline-test", snapshot_hash="a"*64,
        created_at="2026-11-27T12:00:00-03:00",
    )

def test_package_is_deterministic_verifiable_and_never_authorizes_import():
    first, second = build(), build()
    assert first.package_id == second.package_id
    assert first.package_hash == second.package_hash
    assert verify_homologation_package(first)
    assert first.import_authorized is False
    assert all(item.status == "pending" for item in first.approval_criteria)
    assert "formal_approval_not_recorded" in first.blocking_reasons

def test_package_serialization_contains_aggregate_traceability_not_source_payload():
    package = build()
    serialized = serialize_homologation_package(package)
    assert "Item sintético" not in serialized
    assert '"traceability"' in serialized
    assert '"approvalCriteria"' in serialized
    assert '"packageHash"' in serialized

def test_package_hash_detects_tampering():
    package = build()
    altered = replace(package, environment="production")
    assert verify_homologation_package(package)
    assert not verify_homologation_package(altered)

def test_package_requires_sha256_and_metadata():
    preflight = run_integrated_migration_preflight({})
    with pytest.raises(ValueError, match="snapshot_hash"):
        build_synthetic_homologation_package(
            preflight, source_system="synthetic", source_baseline="b",
            snapshot_hash="not-a-hash", created_at="now",
        )
