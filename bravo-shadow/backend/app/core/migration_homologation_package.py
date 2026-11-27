"""Deterministic, privacy-safe synthetic homologation dossier.

This is an assessment artifact only. It does not grant import authorization,
persist approvals, read files, or perform I/O.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re

from app.core.migration_integrated_preflight import IntegratedMigrationPreflight

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_FORMAT_VERSION = 1

@dataclass(frozen=True, slots=True)
class HomologationTrace:
    check_id: str
    component: str
    status: str
    measured_items: int
    issue_codes: tuple[str, ...]

@dataclass(frozen=True, slots=True)
class ApprovalCriterion:
    criterion_id: str
    description: str
    status: str

@dataclass(frozen=True, slots=True)
class SyntheticHomologationPackage:
    format_version: int
    package_id: str
    package_hash: str
    source_system: str
    source_baseline: str
    snapshot_hash: str
    created_at: str
    environment: str
    assessor_version: str
    preflight_status: str
    import_authorized: bool
    collection_totals: tuple[tuple[str, int], ...]
    traceability: tuple[HomologationTrace, ...]
    approval_criteria: tuple[ApprovalCriterion, ...]
    blocking_reasons: tuple[str, ...]

def _canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)

def _payload(package: SyntheticHomologationPackage) -> dict[str, object]:
    return {
        "formatVersion": package.format_version,
        "packageId": package.package_id,
        "sourceSystem": package.source_system,
        "sourceBaseline": package.source_baseline,
        "snapshotHash": package.snapshot_hash,
        "createdAt": package.created_at,
        "environment": package.environment,
        "assessorVersion": package.assessor_version,
        "preflightStatus": package.preflight_status,
        "importAuthorized": package.import_authorized,
        "collectionTotals": [[name, count] for name, count in package.collection_totals],
        "traceability": [
            {"checkId": item.check_id, "component": item.component,
             "status": item.status, "measuredItems": item.measured_items,
             "issueCodes": list(item.issue_codes)}
            for item in package.traceability
        ],
        "approvalCriteria": [
            {"criterionId": item.criterion_id, "description": item.description,
             "status": item.status}
            for item in package.approval_criteria
        ],
        "blockingReasons": list(package.blocking_reasons),
    }

def serialize_homologation_package(package: SyntheticHomologationPackage) -> str:
    payload = _payload(package)
    payload["packageHash"] = package.package_hash
    return _canonical(payload)

def verify_homologation_package(package: SyntheticHomologationPackage) -> bool:
    digest = hashlib.sha256(_canonical(_payload(package)).encode("utf-8")).hexdigest()
    return digest == package.package_hash

def build_synthetic_homologation_package(
    preflight: IntegratedMigrationPreflight,
    *,
    source_system: str,
    source_baseline: str,
    snapshot_hash: str,
    created_at: str,
    environment: str = "shadow-synthetic",
    assessor_version: str = "1.0.0",
) -> SyntheticHomologationPackage:
    """Build an immutable dossier from an integrated in-memory assessment."""
    for name, value in (
        ("source_system", source_system), ("source_baseline", source_baseline),
        ("created_at", created_at), ("environment", environment),
        ("assessor_version", assessor_version),
    ):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} deve ser texto não vazio.")
    if not isinstance(snapshot_hash, str) or not _SHA256.fullmatch(snapshot_hash):
        raise ValueError("snapshot_hash deve conter SHA-256 hexadecimal minúsculo.")

    inventory = preflight.source_inventory
    compatibility = preflight.compatibility
    references = preflight.references
    special = preflight.specialized_contracts
    values = preflight.value_summary

    collection_totals = tuple(sorted(
        (item.name, item.records_total) for item in inventory.collections
    ))
    trace = (
        HomologationTrace(
            "SRC-001", "source_inventory",
            "passed" if inventory.valid_collection_container and not inventory.issue_codes else "blocked",
            len(inventory.collections), inventory.issue_codes,
        ),
        HomologationTrace(
            "MAP-001", "target_compatibility",
            "passed" if not compatibility.unmapped_source_collections
                and not compatibility.unmapped_target_collections
                and not compatibility.mapping_conflicts
                and all(item.status in {"compatible", "compatible_with_optional_gaps"}
                        for item in compatibility.assessments) else "review_required",
            len(compatibility.assessments),
            tuple(sorted(
                (["unmapped_source_collections"] if compatibility.unmapped_source_collections else [])
                + (["unmapped_target_collections"] if compatibility.unmapped_target_collections else [])
                + (["collection_mapping_conflicts"] if compatibility.mapping_conflicts else [])
            )),
        ),
        HomologationTrace(
            "REF-001", "reference_reconciliation",
            "passed" if references.assessments and all(
                item.status == "references_resolved" for item in references.assessments
            ) else "review_required",
            len(references.assessments),
            tuple(sorted({
                "reference_reconciliation_review"
                for item in references.assessments if item.status != "references_resolved"
            })),
        ),
        HomologationTrace(
            "DOM-001", "specialized_contracts", "review_required",
            len(special.assessments),
            ("specialized_domain_approval_pending",)
            if special.assessments or special.unassessed_domains else (),
        ),
        HomologationTrace(
            "VAL-001", "special_value_assessment",
            "passed" if values.records_with_issues == 0 else "review_required",
            values.records_assessed,
            tuple(code for code, _ in values.issue_counts),
        ),
    )
    criteria = (
        ApprovalCriterion("APR-001", "Snapshot sintético e origem formalmente confirmados.", "pending"),
        ApprovalCriterion("APR-002", "Mapeamento de todas as coleções e campos aprovado.", "pending"),
        ApprovalCriterion("APR-003", "Conversões numéricas, datas e fusos aprovados com relatório de perdas.", "pending"),
        ApprovalCriterion("APR-004", "Referências e chaves estrangeiras reconciliadas.", "pending"),
        ApprovalCriterion("APR-005", "Condomínio singleton localizado e validado manualmente.", "pending"),
        ApprovalCriterion("APR-006", "Codec, storage, MIME, limites e autorização de documentos aprovados.", "pending"),
        ApprovalCriterion("APR-007", "Regras de saldo, movimentos e exceções de estoque aprovadas.", "pending"),
        ApprovalCriterion("APR-008", "DDL executável e adaptador Postgres comparados e homologados.", "pending"),
        ApprovalCriterion("APR-009", "Segurança, autorização, auditoria e plano de reversão aprovados.", "pending"),
        ApprovalCriterion("APR-010", "Responsável autorizado aprovou formalmente a importação sintética.", "pending"),
    )
    # Criteria are deliberately pending: this artifact cannot record approvals.
    identity = {
        "sourceSystem": source_system, "sourceBaseline": source_baseline,
        "snapshotHash": snapshot_hash, "createdAt": created_at,
        "environment": environment, "assessorVersion": assessor_version,
    }
    package_id = "homologation-" + hashlib.sha256(_canonical(identity).encode("utf-8")).hexdigest()
    draft = SyntheticHomologationPackage(
        format_version=_FORMAT_VERSION, package_id=package_id, package_hash="",
        source_system=source_system, source_baseline=source_baseline,
        snapshot_hash=snapshot_hash, created_at=created_at, environment=environment,
        assessor_version=assessor_version, preflight_status=preflight.status,
        import_authorized=False, collection_totals=collection_totals,
        traceability=trace, approval_criteria=criteria,
        blocking_reasons=tuple(sorted(set(preflight.blocking_reasons) |
                                      {"formal_approval_not_recorded"})),
    )
    digest = hashlib.sha256(_canonical(_payload(draft)).encode("utf-8")).hexdigest()
    return SyntheticHomologationPackage(**{
        **draft.__dict__, "package_hash": digest
    }) if hasattr(draft, "__dict__") else SyntheticHomologationPackage(
        format_version=draft.format_version, package_id=draft.package_id,
        package_hash=digest, source_system=draft.source_system,
        source_baseline=draft.source_baseline, snapshot_hash=draft.snapshot_hash,
        created_at=draft.created_at, environment=draft.environment,
        assessor_version=draft.assessor_version, preflight_status=draft.preflight_status,
        import_authorized=False, collection_totals=draft.collection_totals,
        traceability=draft.traceability, approval_criteria=draft.approval_criteria,
        blocking_reasons=draft.blocking_reasons,
    )
