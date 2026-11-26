import pytest

from app.core.migration_decisions import build_decision_register
from app.core.migration_review import (
    ReviewValidationError,
    append_review,
    create_review_ledger,
)
from test_migration_decisions import setup_batch


def setup_review():
    _, _, preflight, manifest = setup_batch()
    register = build_decision_register(manifest, preflight)
    ledger = create_review_ledger(register)
    return register, ledger, register.pending[0].decision_id


def test_review_appends_version_one_without_mutating_original_ledger():
    register, ledger, decision_id = setup_review()

    updated = append_review(
        ledger,
        register,
        event_id="evt-001",
        decision_id=decision_id,
        expected_version=0,
        reviewer_id="reviewer@example.test",
        choice="keep_blocked",
        rationale="A referência precisa ser conferida.",
        reviewed_at="2026-11-26T15:30:00-03:00",
    )

    assert ledger.events == ()
    assert len(updated.events) == 1
    assert updated.events[0].version == 1
    assert updated.version_for(decision_id) == 1
    assert updated.history_for(decision_id)[0].reviewer_id == "reviewer@example.test"


def test_new_review_versions_preserve_full_history():
    register, ledger, decision_id = setup_review()
    first = append_review(
        ledger, register,
        event_id="evt-001", decision_id=decision_id, expected_version=0,
        reviewer_id="reviewer-1", choice="keep_blocked",
        rationale="Manter bloqueado.", reviewed_at="2026-11-26T15:30:00-03:00",
    )
    second = append_review(
        first, register,
        event_id="evt-002", decision_id=decision_id, expected_version=1,
        reviewer_id="reviewer-2", choice="request_more_information",
        rationale="Solicitar evidência adicional.", reviewed_at="2026-11-26T15:40:00-03:00",
    )

    assert [event.version for event in second.history_for(decision_id)] == [1, 2]
    assert [event.event_id for event in second.history_for(decision_id)] == ["evt-001", "evt-002"]


def test_stale_version_is_rejected():
    register, ledger, decision_id = setup_review()
    with pytest.raises(ReviewValidationError, match="stale_review_version"):
        append_review(
            ledger, register,
            event_id="evt-001", decision_id=decision_id, expected_version=1,
            reviewer_id="reviewer", choice="keep_blocked",
            rationale="Não executar.", reviewed_at="2026-11-26T15:30:00-03:00",
        )


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("reviewer_id", " ", "reviewer_required"),
        ("rationale", " ", "rationale_required"),
        ("reviewed_at", "", "reviewed_at_required"),
        ("event_id", "", "duplicate_or_empty_event_id"),
    ],
)
def test_required_review_fields_are_validated(field, value, error):
    register, ledger, decision_id = setup_review()
    args = dict(
        event_id="evt-001", decision_id=decision_id, expected_version=0,
        reviewer_id="reviewer", choice="keep_blocked",
        rationale="Justificativa.", reviewed_at="2026-11-26T15:30:00-03:00",
    )
    args[field] = value
    with pytest.raises(ReviewValidationError, match=error):
        append_review(ledger, register, **args)


def test_review_cannot_target_unknown_decision_or_other_manifest():
    register, ledger, decision_id = setup_review()
    with pytest.raises(ReviewValidationError, match="unknown_decision"):
        append_review(
            ledger, register,
            event_id="evt-001", decision_id="unknown", expected_version=0,
            reviewer_id="reviewer", choice="keep_blocked",
            rationale="Justificativa.", reviewed_at="2026-11-26T15:30:00-03:00",
        )
    from dataclasses import replace
    other_register = replace(register, manifest_hash="f" * 64)
    with pytest.raises(ReviewValidationError, match="ledger_batch_mismatch"):
        append_review(
            ledger, other_register,
            event_id="evt-002", decision_id=decision_id, expected_version=0,
            reviewer_id="reviewer", choice="keep_blocked",
            rationale="Justificativa.", reviewed_at="2026-11-26T15:30:00-03:00",
        )



def test_review_history_serializes_deterministically_and_verifies():
    from app.core.migration_review import serialize_review_ledger, verify_review_ledger

    register, ledger, decision_id = setup_review()
    reviewed = append_review(
        ledger, register,
        event_id="evt-integrity", decision_id=decision_id, expected_version=0,
        reviewer_id="reviewer", choice="keep_blocked",
        rationale="Aguardando conferência.", reviewed_at="2026-11-26T15:45:00-03:00",
    )

    assert serialize_review_ledger(reviewed) == serialize_review_ledger(reviewed)
    assert '"formatVersion":1' in serialize_review_ledger(reviewed)
    assert verify_review_ledger(reviewed, register) is True


def test_review_history_verifier_rejects_duplicate_or_broken_versions():
    from dataclasses import replace
    from app.core.migration_review import verify_review_ledger

    register, ledger, decision_id = setup_review()
    first = append_review(
        ledger, register,
        event_id="evt-1", decision_id=decision_id, expected_version=0,
        reviewer_id="reviewer", choice="keep_blocked",
        rationale="Manter bloqueado.", reviewed_at="2026-11-26T15:30:00-03:00",
    )
    broken_event = replace(first.events[0], version=3)
    broken = replace(first, events=(broken_event,))

    assert verify_review_ledger(first, register) is True
    assert verify_review_ledger(broken, register) is False
    assert verify_review_ledger(first, replace(register, manifest_hash="c" * 64)) is False


def test_review_history_is_bound_to_original_manifest():
    from dataclasses import replace
    from app.core.migration_review import verify_review_ledger

    register, ledger, _ = setup_review()
    assert verify_review_ledger(ledger, register) is True
    assert verify_review_ledger(ledger, replace(register, manifest_hash="a" * 64)) is False

def test_event_id_is_globally_unique_across_decisions():
    register, ledger, first_decision = setup_review()
    first = append_review(
        ledger, register,
        event_id="globally-unique-event", decision_id=first_decision,
        expected_version=0, reviewer_id="reviewer",
        choice="keep_blocked", rationale="Manter bloqueado.",
        reviewed_at="2026-11-26T16:10:00-03:00",
    )
    second_decision = next(
        item.decision_id for item in register.pending
        if item.decision_id != first_decision
    )

    with pytest.raises(ReviewValidationError, match="duplicate_or_empty_event_id"):
        append_review(
            first, register,
            event_id="globally-unique-event", decision_id=second_decision,
            expected_version=0, reviewer_id="reviewer",
            choice="keep_blocked", rationale="Manter bloqueado.",
            reviewed_at="2026-11-26T16:11:00-03:00",
        )


def test_invalid_choice_is_rejected_and_tampered_choice_fails_verification():
    from dataclasses import replace
    from app.core.migration_review import verify_review_ledger

    register, ledger, decision_id = setup_review()
    with pytest.raises(ReviewValidationError, match="invalid_review_choice"):
        append_review(
            ledger, register,
            event_id="evt-invalid-choice", decision_id=decision_id,
            expected_version=0, reviewer_id="reviewer",
            choice="import_now", rationale="Não deve executar.",
            reviewed_at="2026-11-26T16:12:00-03:00",
        )

    valid = append_review(
        ledger, register,
        event_id="evt-valid-choice", decision_id=decision_id,
        expected_version=0, reviewer_id="reviewer",
        choice="keep_blocked", rationale="Manter bloqueado.",
        reviewed_at="2026-11-26T16:13:00-03:00",
    )
    altered_event = replace(valid.events[0], choice="import_now")
    altered_ledger = replace(valid, events=(altered_event,))

    assert verify_review_ledger(valid, register) is True
    assert verify_review_ledger(altered_ledger, register) is False

