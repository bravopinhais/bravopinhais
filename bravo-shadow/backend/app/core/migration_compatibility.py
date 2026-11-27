"""Declarative, non-transforming compatibility assessment for migration fields.

Contracts describe the current Shadow input schemas. Field-name matching is
exact by design: this module does not guess legacy aliases, coerce values,
apply defaults, or produce import payloads.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from app.core.migration_source_inventory import CollectionInventory, FieldInventory, SourceInventory


@dataclass(frozen=True, slots=True)
class TargetField:
    name: str
    expected_type: str
    required: bool


@dataclass(frozen=True, slots=True)
class TargetCollection:
    name: str
    fields: tuple[TargetField, ...]


@dataclass(frozen=True, slots=True)
class FieldAssessment:
    name: str
    status: str
    expected_type: str
    observed_types: tuple[tuple[str, int], ...]
    records_present: int


@dataclass(frozen=True, slots=True)
class CollectionAssessment:
    source_collection: str
    target_collection: str
    source_records: int
    status: str
    fields: tuple[FieldAssessment, ...]
    missing_required: tuple[str, ...]
    missing_optional: tuple[str, ...]
    unexpected_source_fields: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CompatibilityReport:
    assessments: tuple[CollectionAssessment, ...]
    unmapped_source_collections: tuple[str, ...]
    unmapped_target_collections: tuple[str, ...]


# These describe current Shadow schemas, not proof of legacy field aliases.
# 'version' is intentionally omitted: it is Shadow-managed metadata.
TARGET_CONTRACTS: tuple[TargetCollection, ...] = (
    TargetCollection("categorias", (
        TargetField("id", "string", True), TargetField("nome", "string", True),
    )),
    TargetCollection("motivos_acerto", (
        TargetField("id", "string", True), TargetField("nome", "string", True),
    )),
    TargetCollection("fornecedores", (
        TargetField("id", "string", True), TargetField("cnpj", "string", True),
        TargetField("razaoSocial", "string", True),
    )),
    TargetCollection("empregados", (
        TargetField("id", "string", True), TargetField("nome", "string", True),
        TargetField("cargo", "string", True), TargetField("empresa", "string", False),
        TargetField("endereco", "string", False), TargetField("telefone", "string", False),
        TargetField("contatoEmergenciaNome", "string", False),
        TargetField("contatoEmergenciaTel", "string", False),
    )),
    TargetCollection("moradores", (
        TargetField("id", "string", True), TargetField("bloco", "string", True),
        TargetField("apartamento", "string", True), TargetField("nome", "string", True),
        TargetField("email", "string", False), TargetField("telefone", "string", False),
        TargetField("cpf", "string", False), TargetField("petNome", "string", False),
        TargetField("vagaGaragem", "string", False),
    )),
    TargetCollection("conselheiros", (
        TargetField("id", "string", True), TargetField("nome", "string", True),
        TargetField("cargo", "string", True), TargetField("BlocoAp", "string", False),
        TargetField("telefone", "string", False),
    )),
    TargetCollection("plano_contas", (
        TargetField("id", "string", True), TargetField("codigo", "string", True),
        TargetField("nome", "string", True), TargetField("tipo", "string", True),
    )),
    TargetCollection("formas_monetarias", (
        TargetField("id", "string", True), TargetField("nome", "string", True),
        TargetField("multaPct", "number", False),
    )),
    TargetCollection("contas_bancarias", (
        TargetField("id", "string", True), TargetField("banco", "string", True),
        TargetField("saldo", "decimal", False),
    )),
)


def _assess_field(source: FieldInventory, target: TargetField) -> FieldAssessment:
    observed = dict(source.value_types)
    if target.expected_type == "decimal":
        compatible = set(observed).issubset({"string"})
        # JSON numbers cannot prove decimal precision was preserved.
        status = "compatible" if compatible else "review_conversion"
    elif target.expected_type == "number":
        compatible = set(observed).issubset({"number"})
        status = "compatible" if compatible else "review_conversion"
    else:
        compatible = set(observed).issubset({"string"})
        status = "compatible" if compatible else "incompatible_type"
    return FieldAssessment(
        name=target.name,
        status=status,
        expected_type=target.expected_type,
        observed_types=source.value_types,
        records_present=source.records_present,
    )


def assess_source_compatibility(
    inventory: SourceInventory,
    *,
    source_to_target: Mapping[str, str] | None = None,
) -> CompatibilityReport:
    """Compare exact field names/types using an explicit collection mapping.

    The default mapping uses identical collection names. Supply
    source_to_target only after the legacy collection names are confirmed.
    """
    mapping = dict(source_to_target or {item.name: item.name for item in TARGET_CONTRACTS})
    target_by_name = {item.name: item for item in TARGET_CONTRACTS}
    source_by_name = {item.name: item for item in inventory.collections}
    assessments: list[CollectionAssessment] = []
    mapped_sources: set[str] = set()
    mapped_targets: set[str] = set()

    for source_name, target_name in sorted(mapping.items()):
        source = source_by_name.get(source_name)
        target = target_by_name.get(target_name)
        if source is None or target is None:
            continue
        mapped_sources.add(source_name)
        mapped_targets.add(target_name)
        source_fields = {item.name: item for item in source.fields}
        target_fields = {item.name: item for item in target.fields}
        field_results = tuple(
            _assess_field(source_fields[field_name], target_field)
            for field_name, target_field in sorted(target_fields.items())
            if field_name in source_fields
        )
        missing_required = tuple(sorted(
            name for name, field in target_fields.items()
            if field.required and name not in source_fields
        ))
        missing_optional = tuple(sorted(
            name for name, field in target_fields.items()
            if not field.required and name not in source_fields
        ))
        unexpected = tuple(sorted(set(source_fields) - set(target_fields)))
        has_type_issue = any(item.status != "compatible" for item in field_results)
        status = "review_required" if missing_required or has_type_issue else (
            "compatible_with_optional_gaps" if missing_optional or unexpected else "compatible"
        )
        assessments.append(CollectionAssessment(
            source_collection=source_name,
            target_collection=target_name,
            source_records=source.records_total,
            status=status,
            fields=field_results,
            missing_required=missing_required,
            missing_optional=missing_optional,
            unexpected_source_fields=unexpected,
        ))

    mapped_sources.update(name for name in mapping if name in source_by_name and name not in mapped_sources)
    mapped_targets.update(name for name in mapping.values() if name in target_by_name and name not in mapped_targets)
    return CompatibilityReport(
        assessments=tuple(assessments),
        unmapped_source_collections=tuple(sorted(set(source_by_name) - mapped_sources)),
        unmapped_target_collections=tuple(sorted(set(target_by_name) - mapped_targets)),
    )
