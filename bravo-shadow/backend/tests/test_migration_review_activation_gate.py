"""Activation gates for the migration-review feature.

These tests intentionally protect the current non-exposed state. They do not
exercise PostgreSQL or authorize any reviewer role.
"""
from app.core.authorization import CAPABILITIES
from app.main import create_app


def test_migration_review_capabilities_remain_unapproved():
    assert "migration_review:read" not in CAPABILITIES
    assert "migration_review:append" not in CAPABILITIES


def test_migration_review_service_is_not_exposed_through_app_state():
    application = create_app(storage_backend="memory")
    assert not hasattr(application.state, "migration_review_service")


def test_no_public_migration_review_route_is_registered():
    application = create_app(storage_backend="memory")
    paths = {route.path for route in application.routes}
    assert not any("migration-review" in path or "migration_review" in path for path in paths)
