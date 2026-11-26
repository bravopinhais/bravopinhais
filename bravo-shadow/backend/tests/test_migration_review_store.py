import threading
from dataclasses import replace

import pytest

from app.core.migration_review import ReviewValidationError
from app.core.migration_review_store import InMemoryReviewLedgerStore
from test_migration_decisions import setup_batch


def setup_store():
    _, _, preflight, manifest = setup_batch()
    from app.core.migration_decisions import build_decision_register

    register = build_decision_register(manifest, preflight)
    return register, register.pending[0].decision_id


def event_args(decision_id, event_id, expected_version):
    return dict(
        event_id=event_id,
        decision_id=decision_id,
        expected_version=expected_version,
        reviewer_id="reviewer@example.test",
        choice="keep_blocked",
        rationale="Manter bloqueado até conferência.",
        reviewed_at="2026-11-26T16:00:00-03:00",
    )


def test_store_initializes_and_reloads_same_immutable_ledger():
    register, _ = setup_store()
    store = InMemoryReviewLedgerStore()

    first = store.load(register)
    second = store.load(register)

    assert first == second
    assert first.events == ()


def test_store_appends_history_and_preserves_previous_versions():
    register, decision_id = setup_store()
    store = InMemoryReviewLedgerStore()

    first = store.append(register, **event_args(decision_id, "evt-1", 0))
    second = store.append(register, **event_args(decision_id, "evt-2", 1))

    assert [event.version for event in second.events] == [1, 2]
    assert [event.event_id for event in first.events] == ["evt-1"]
    assert [event.event_id for event in store.load(register).events] == ["evt-1", "evt-2"]


def test_store_rejects_stale_version_and_duplicate_event_id():
    register, decision_id = setup_store()
    store = InMemoryReviewLedgerStore()
    store.append(register, **event_args(decision_id, "evt-1", 0))

    with pytest.raises(ReviewValidationError, match="stale_review_version"):
        store.append(register, **event_args(decision_id, "evt-stale", 0))
    with pytest.raises(ReviewValidationError, match="duplicate_or_empty_event_id"):
        store.append(register, **event_args(decision_id, "evt-1", 1))


def test_store_rejects_same_batch_id_with_different_manifest():
    register, _ = setup_store()
    store = InMemoryReviewLedgerStore()
    store.load(register)
    other_manifest = replace(register, manifest_hash="f" * 64)

    with pytest.raises(ReviewValidationError, match="stored_ledger_binding_or_integrity_error"):
        store.load(other_manifest)


def test_two_concurrent_writers_with_same_expected_version_only_one_wins():
    register, decision_id = setup_store()
    store = InMemoryReviewLedgerStore()
    barrier = threading.Barrier(2)
    outcomes = []

    def writer(event_id):
        barrier.wait()
        try:
            store.append(register, **event_args(decision_id, event_id, 0))
            outcomes.append("saved")
        except ReviewValidationError as exc:
            outcomes.append(str(exc))

    threads = [
        threading.Thread(target=writer, args=("evt-a",)),
        threading.Thread(target=writer, args=("evt-b",)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert outcomes.count("saved") == 1
    assert outcomes.count("stale_review_version") == 1
    assert len(store.load(register).events) == 1
