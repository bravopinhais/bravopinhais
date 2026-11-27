import base64, zlib
from app.core.migration_special_value_assessment import assess_special_record_values

def codes(report):
    return {issue.code for issue in report.issues}

def test_financeiro_flags_legacy_number_without_echoing_value():
    report = assess_special_record_values("financeiro", {"tipo":"Receber", "valor":10.25})
    assert "decimal_precision_unproven" in codes(report)
    assert report.status == "review_required"
    assert "10.25" not in repr(report)

def test_literal_and_quantity_constraints_are_checked_without_mutation():
    record = {"tipo":"entrada", "quantidade":-1}
    before = dict(record)
    report = assess_special_record_values("acertos_estoque", record)
    assert {"invalid_literal", "negative_not_allowed", "numeric_conversion_review", "datetime_timezone_review"} <= codes(report)
    assert record == before

def test_three_decimal_quantity_is_within_shape_but_conversion_still_requires_review():
    report = assess_special_record_values("estoque", {"quantidade":1.125})
    assert "numeric_conversion_review" in codes(report)
    assert "numeric_precision_exceeded" not in codes(report)

def test_document_codec_is_validated_and_only_metadata_is_returned():
    packed = base64.b64encode(zlib.compress(b"synthetic-only")).decode()
    report = assess_special_record_values("documentos", {"arquivoCompactadoGzip":packed})
    assert report.issues == ()
    invalid = assess_special_record_values("documentos", {"arquivoCompactadoGzip":"invalid"})
    assert "compressed_document_invalid" in codes(invalid)

def test_unknown_contract_is_explicitly_rejected():
    assert assess_special_record_values("unknown", {}).status == "unsupported_contract"
