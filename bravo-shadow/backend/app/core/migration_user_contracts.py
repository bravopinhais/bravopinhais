"""Legacy user-record assessment with credential exclusion.

The field list is based only on the static DEFAULT_DATA example. It is not a
production schema or import authorization. Authentication remains Google-only.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.core.migration_source_inventory import SourceInventory


@dataclass(frozen=True, slots=True)
class UserCollectionAssessment:
    status: str
    record_count: int | None
    missing_required: tuple[str, ...]
    partially_populated: tuple[str, ...]
    unexpected_fields: tuple[str, ...]
    forbidden_fields: tuple[str, ...]
    type_mismatches: tuple[str, ...]
    review_reasons: tuple[str, ...]


# Fields observed in the legacy DEFAULT_DATA user example. Credential fields
# are intentionally absent; Google identity is re-established in Shadow.
_USER_FIELD_TYPES = {
    "id": "string",
    "usuario": "string",
    "nome": "string",
    "email": "string",
    "cargo": "string",
    "loja": "string",
    "perfil": "string",
    "status": "string",
    "primeiroAcesso": "boolean",
}
_FORBIDDEN_FIELD_NAMES = {
    "senha", "senhaHash", "password", "passwordHash", "token", "accessToken",
    "refreshToken", "cookie", "session", "sessionToken", "apiKey", "secret",
}


def assess_legacy_users(inventory: SourceInventory) -> UserCollectionAssessment:
    """Inspect users by exact key; never return values or authorize import."""
    source = next((item for item in inventory.collections if item.name == "usuarios"), None)
    if source is None:
        return UserCollectionAssessment(
            "source_collection_not_found", None, tuple(_USER_FIELD_TYPES), (), (), (), (),
            ("Coleção usuarios não localizada pelo nome exato.",),
        )

    fields = {field.name: field for field in source.fields}
    required = tuple(_USER_FIELD_TYPES)
    missing = tuple(sorted(name for name in required if name not in fields))
    partial = tuple(sorted(
        name for name in required
        if name in fields and fields[name].records_present < source.records_total
    ))
    forbidden = tuple(sorted(set(fields) & _FORBIDDEN_FIELD_NAMES))
    unexpected = tuple(sorted(set(fields) - set(_USER_FIELD_TYPES) - _FORBIDDEN_FIELD_NAMES))
    mismatches = tuple(sorted(
        name for name, expected in _USER_FIELD_TYPES.items()
        if name in fields
        and {kind for kind, count in fields[name].value_types if count} != {expected}
    ))
    reasons = [
        "Conta interna, perfil e status exigem reconciliação com o cadastro atual.",
        "Identidade Google verificada é obrigatória; não migrar credenciais legadas.",
    ]
    if source.records_total == 0:
        reasons.append("Coleção vazia não comprova formato.")
    if missing:
        reasons.append("Campos esperados ausentes.")
    if partial:
        reasons.append("Campos parcialmente preenchidos exigem revisão.")
    if forbidden:
        reasons.append("Campo de credencial/sessão detectado; excluir do fluxo e revisar origem.")
    if unexpected:
        reasons.append("Campos não catalogados exigem decisão explícita.")
    if mismatches:
        reasons.append("Tipos divergentes exigem revisão.")
    return UserCollectionAssessment(
        "review_required", source.records_total, missing, partial,
        unexpected, forbidden, mismatches, tuple(reasons),
    )
