"""Conservative structural contracts for low-risk reference collections.

Assessment only: these contracts do not transform data or authorize import.
Field shapes are limited to fields observed in the legacy DEFAULT_DATA audit.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.core.migration_source_inventory import SourceInventory


@dataclass(frozen=True, slots=True)
class ReferenceContractAssessment:
    collection: str
    status: str
    record_count: int | None
    missing_required: tuple[str, ...]
    partially_populated: tuple[str, ...]
    unexpected_fields: tuple[str, ...]
    type_mismatches: tuple[str, ...]
    review_reasons: tuple[str, ...]


_REFERENCE_FIELDS = {
    "plano_contas": ("id", "codigo", "nome", "tipo"),
    "motivos_acerto_estoque": ("id", "nome"),
}


def assess_reference_contracts(inventory: SourceInventory) -> tuple[ReferenceContractAssessment, ...]:
    """Check only observed names/types; every result remains review-only."""
    by_name = {item.name: item for item in inventory.collections}
    results = []
    for collection, required_fields in _REFERENCE_FIELDS.items():
        source = by_name.get(collection)
        if source is None:
            results.append(ReferenceContractAssessment(
                collection, "source_collection_not_found", None,
                required_fields, (), (), (),
                ("Coleção não localizada pelo nome exato; não inferir aliases.",),
            ))
            continue
        fields = {field.name: field for field in source.fields}
        missing = tuple(sorted(name for name in required_fields if name not in fields))
        partial = tuple(sorted(
            name for name in required_fields
            if name in fields and fields[name].records_present < source.records_total
        ))
        unexpected = tuple(sorted(set(fields) - set(required_fields)))
        mismatches = tuple(sorted(
            name for name in required_fields
            if name in fields
            and {kind for kind, count in fields[name].value_types if count}
            != {"string"}
        ))
        reasons = ["Formato observado não comprova semântica nem integridade referencial."]
        if source.records_total == 0:
            reasons.append("Coleção vazia não comprova compatibilidade.")
        if missing:
            reasons.append("Campos obrigatórios ausentes.")
        if partial:
            reasons.append("Campos parcialmente preenchidos exigem revisão.")
        if unexpected:
            reasons.append("Campos adicionais exigem decisão explícita.")
        if mismatches:
            reasons.append("Tipos divergem do formato textual observado.")
        results.append(ReferenceContractAssessment(
            collection, "review_required", source.records_total,
            missing, partial, unexpected, mismatches, tuple(reasons),
        ))
    return tuple(results)
