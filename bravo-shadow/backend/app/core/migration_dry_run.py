"""Pure, read-only migration dry-run planner."""
from __future__ import annotations
from dataclasses import dataclass
import hashlib, json
from typing import Any, Mapping, Sequence
from app.core.migration_pre_import_approval import ApprovalEvidenceResult
from app.core.migration_pre_import_manifest import PreImportManifest

DRY_RUN_VERSION = "1"
RECORD_HASH_VERSION = "json-sort-keys-utf8-no-whitespace-v1"
ALLOWED_TARGETS = frozenset({"categorias","motivos_acerto","fornecedores","empregados","moradores","conselheiros","plano_contas","formas_monetarias","contas_bancarias","estoque","acertos_estoque","financeiro","documentos","condominio"})

@dataclass(frozen=True, slots=True)
class ExistingSourceLink:
    source_system: str
    source_collection: str
    legacy_id: str
    record_sha256: str

@dataclass(frozen=True, slots=True)
class RecordDecision:
    source_collection: str
    target_collection: str
    identity_fingerprint: str
    record_sha256: str | None
    classification: str

@dataclass(frozen=True, slots=True)
class Discrepancy:
    code: str
    count: int

@dataclass(frozen=True, slots=True)
class DryRunReport:
    dry_run_version: str
    manifest_sha256: str
    raw_source_sha256: str
    approval_verified: bool
    writes_authorized: bool
    status: str
    source_records: int
    planned_inserts: int
    already_applied: int
    changed_source_conflicts: int
    destination_id_collisions: int
    invalid_records: int
    duplicate_source_identities: int
    simulated_rollback: bool
    simulated_rollback_count: int
    plan_sha256: str
    decisions: tuple[RecordDecision, ...]
    discrepancies: tuple[Discrepancy, ...]

def _hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def _identity_hash(system: str, collection: str, legacy_id: str) -> str:
    return _hash([system, collection, legacy_id])

def build_migration_dry_run(
    manifest: PreImportManifest,
    approval: ApprovalEvidenceResult,
    collections: Mapping[str, Any],
    *,
    source_to_target: Mapping[str, str],
    existing_source_links: Sequence[ExistingSourceLink] = (),
    existing_target_ids: Mapping[str, Sequence[str]] | None = None,
    simulate_failure_after: int | None = None,
) -> DryRunReport:
    """Classify records against read-only state snapshots; never persist or mutate."""
    if not isinstance(manifest, PreImportManifest) or not isinstance(approval, ApprovalEvidenceResult):
        raise TypeError("manifesto ou aprovação inválidos.")
    if not approval.valid or not approval.eligible_for_dry_run or approval.writes_authorized or manifest.writes_authorized:
        raise ValueError("aprovação elegível para dry-run é obrigatória; escrita proibida.")
    if manifest.readiness != "awaiting_human_approval":
        raise ValueError("manifesto não está liberado para dry-run.")
    if not isinstance(collections, Mapping) or not isinstance(source_to_target, Mapping) or not source_to_target:
        raise ValueError("coleções e mapeamento explícito são obrigatórios.")
    if simulate_failure_after is not None and (isinstance(simulate_failure_after, bool) or not isinstance(simulate_failure_after, int) or simulate_failure_after <= 0):
        raise ValueError("ponto de falha simulado inválido.")
    mapping = {}
    for src, dst in source_to_target.items():
        if not isinstance(src, str) or not src.strip() or dst not in ALLOWED_TARGETS:
            raise ValueError("mapeamento inválido ou destino não permitido.")
        mapping[src] = dst
    if len(set(mapping.values())) != len(mapping):
        raise ValueError("mapeamento muitos-para-um exige revisão explícita.")
    links = {}
    for link in existing_source_links:
        if not isinstance(link, ExistingSourceLink):
            raise TypeError("vínculo de origem inválido.")
        key = (link.source_system, link.source_collection, link.legacy_id)
        if key in links:
            raise ValueError("snapshot de vínculos contém identidade duplicada.")
        links[key] = link.record_sha256
    target_ids = {name: set(ids) for name, ids in (existing_target_ids or {}).items()}
    counts = {k: 0 for k in ("planned_insert","already_applied","conflict_changed_source","destination_id_collision","invalid_record","duplicate_source_identity")}
    decisions, seen, total = [], set(), 0
    for src, dst in sorted(mapping.items()):
        records = collections.get(src, ())
        if not isinstance(records, (list, tuple)):
            raise ValueError("coleção ausente ou inválida: " + src)
        for record in records:
            total += 1
            if not isinstance(record, Mapping):
                counts["invalid_record"] += 1
                decisions.append(RecordDecision(src,dst,_identity_hash(manifest.source_system,src,"invalid:"+str(total)),None,"invalid_record"))
                continue
            legacy_id = record.get("id")
            if not isinstance(legacy_id, str) or not legacy_id:
                counts["invalid_record"] += 1
                decisions.append(RecordDecision(src,dst,_identity_hash(manifest.source_system,src,"missing:"+str(total)),None,"invalid_record"))
                continue
            identity = (manifest.source_system,src,legacy_id)
            fp = _identity_hash(*identity)
            if identity in seen:
                counts["duplicate_source_identity"] += 1
                decisions.append(RecordDecision(src,dst,fp,None,"duplicate_source_identity"))
                continue
            seen.add(identity)
            try:
                digest = _hash(record)
            except (TypeError, ValueError, RecursionError):
                counts["invalid_record"] += 1
                decisions.append(RecordDecision(src,dst,fp,None,"invalid_record"))
                continue
            old_hash = links.get(identity)
            if old_hash is not None:
                classification = "already_applied" if old_hash == digest else "conflict_changed_source"
            elif legacy_id in target_ids.get(dst,set()):
                classification = "destination_id_collision"
            else:
                classification = "planned_insert"
            counts[classification] += 1
            decisions.append(RecordDecision(src,dst,fp,digest,classification))
    planned = counts["planned_insert"]
    rollback = simulate_failure_after is not None and planned >= simulate_failure_after
    rollback_count = simulate_failure_after if rollback else 0
    status = "simulated_rollback" if rollback else "dry_run_complete"
    discrepancy_codes = ("conflict_changed_source","destination_id_collision","invalid_record","duplicate_source_identity")
    discrepancies = tuple(Discrepancy(code,counts[code]) for code in discrepancy_codes if counts[code])
    plan_hash = _hash({"version":DRY_RUN_VERSION,"manifest":manifest.manifest_sha256,"hashVersion":RECORD_HASH_VERSION,"decisions":[[d.source_collection,d.target_collection,d.identity_fingerprint,d.record_sha256,d.classification] for d in decisions],"rollback":rollback,"rollbackCount":rollback_count})
    return DryRunReport(DRY_RUN_VERSION,manifest.manifest_sha256,manifest.raw_source_sha256,True,False,status,total,planned,counts["already_applied"],counts["conflict_changed_source"],counts["destination_id_collision"],counts["invalid_record"],counts["duplicate_source_identity"],rollback,rollback_count,plan_hash,tuple(decisions),discrepancies)
