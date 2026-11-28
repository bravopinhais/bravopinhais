"""Evidence classification for legacy collections empty in DEFAULT_DATA.

An empty default array proves the collection key exists, not its schema.
This module deliberately does not infer fields or authorize migration.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.core.migration_source_inventory import SourceInventory


@dataclass(frozen=True, slots=True)
class EmptyCollectionEvidence:
    legacy_key: str
    status: str
    record_count: int | None
    observed_fields: tuple[str, ...]
    import_allowed: bool
    reason: str


EMPTY_DEFAULT_COLLECTIONS = frozenset({
    "conselheiros",
    "formas_monetarias",
    "contas_bancarias",
    "moradores",
    "fornecedores",
    "empregados",
    "categorias",
    "logs",
})


def assess_empty_default_collections(
    inventory: SourceInventory,
) -> tuple[EmptyCollectionEvidence, ...]:
    """Classify only the named empty defaults; never infer their record schema."""
    lookup = {item.name: item for item in inventory.collections}
    results: list[EmptyCollectionEvidence] = []
    for key in sorted(EMPTY_DEFAULT_COLLECTIONS):
        item = lookup.get(key)
        if item is None:
            status, count, fields, reason = (
                "source_collection_not_found", None, (),
                "A chave exata não está presente no inventário.",
            )
        elif item.records_total == 0:
            status, count, fields, reason = (
                "schema_unobserved_empty_default", 0, (),
                "A lista padrão está vazia; nenhum campo ou tipo de registro pode ser inferido.",
            )
        else:
            status, count, fields, reason = (
                "records_present_requires_contract", item.records_total,
                tuple(field.name for field in item.fields),
                "Há registros; campos e tipos observados ainda exigem contrato e revisão.",
            )
        results.append(EmptyCollectionEvidence(
            key, status, count, fields, False, reason,
        ))
    return tuple(results)
