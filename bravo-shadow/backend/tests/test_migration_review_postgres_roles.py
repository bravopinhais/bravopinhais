from __future__ import annotations

import pytest

from app.core.migration_review import ReviewValidationError
from app.core.migration_review_postgres_roles import (
    PostgresReviewRuntimeStore,
    PostgresReviewSnapshotInitializer,
)
from test_migration_decisions import setup_batch
from app.core.migration_decisions import build_decision_register
from test_migration_review_postgres import FakeDatabase


def test_runtime_facade_does_not_expose_snapshot_initialization():
    assert not hasattr(PostgresReviewRuntimeStore, "initialize")
    assert hasattr(PostgresReviewRuntimeStore, "load")
    assert hasattr(PostgresReviewRuntimeStore, "append")


def test_initializer_and_runtime_use_separate_connection_factories():
    _, _, preflight, manifest = setup_batch()
    register = build_decision_register(manifest, preflight)
    preparation_db = FakeDatabase()
    runtime_db = FakeDatabase()

    initializer = PostgresReviewSnapshotInitializer(preparation_db.connect)
    runtime = PostgresReviewRuntimeStore(runtime_db.connect)

    initialized = initializer.initialize(register)
    assert initialized.events == ()
    assert len(preparation_db.batches) == 1

    # The runtime facade cannot create its own snapshot and fails closed
    # when its independently wired database has not been prepared.
    with pytest.raises(ReviewValidationError, match="review_batch_not_initialized"):
        runtime.load(register)
    assert runtime_db.batches == {}
