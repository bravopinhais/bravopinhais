"""Bounded, read-only reader for synthetic or authorized migration envelopes.

This module decodes UTF-8 JSON bytes only. It performs no filesystem access,
network access, database access, decompression, or persistence. The raw file
digest is reported separately from the envelope's snapshotHash because the
latter is defined by the export contract and must not be guessed here.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

from app.core.migration_envelope import EnvelopeValidation, validate_batch_envelope

MAX_ENVELOPE_BYTES = 10 * 1024 * 1024


class EnvelopeReadError(ValueError):
    """Raised when the supplied byte stream cannot be safely decoded."""


@dataclass(frozen=True, slots=True)
class EnvelopeReadResult:
    envelope: Mapping[str, Any]
    validation: EnvelopeValidation
    raw_file_sha256: str
    byte_length: int


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise EnvelopeReadError("json_duplicate_key")
        result[key] = value
    return result


def _reject_non_finite(value: str) -> None:
    raise EnvelopeReadError("json_non_finite_number")


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def read_envelope_bytes(
    raw: bytes,
    *,
    max_bytes: int = MAX_ENVELOPE_BYTES,
) -> EnvelopeReadResult:
    """Decode and validate a bounded JSON envelope without mutating input.

    The raw file digest is evidence for a later manifest/reconciliation step;
    it is deliberately not compared to snapshotHash, whose canonical scope is
    defined by the exporter rather than by this reader.
    """
    if not isinstance(raw, bytes):
        raise TypeError("raw deve ser bytes.")
    if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes <= 0:
        raise ValueError("max_bytes deve ser inteiro positivo.")
    if len(raw) > max_bytes:
        raise EnvelopeReadError("envelope_too_large")
    if not raw:
        raise EnvelopeReadError("envelope_empty")

    try:
        decoded = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise EnvelopeReadError("envelope_not_utf8") from exc

    try:
        parsed = json.loads(
            decoded,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_non_finite,
        )
    except EnvelopeReadError:
        raise
    except (json.JSONDecodeError, RecursionError) as exc:
        raise EnvelopeReadError("envelope_invalid_json") from exc

    validation = validate_batch_envelope(parsed)
    if not validation.valid:
        codes = ",".join(issue.code for issue in validation.issues)
        raise EnvelopeReadError(f"envelope_invalid_structure:{codes}")

    frozen = _freeze(parsed)
    return EnvelopeReadResult(
        envelope=frozen,
        validation=validation,
        raw_file_sha256=hashlib.sha256(raw).hexdigest(),
        byte_length=len(raw),
    )
