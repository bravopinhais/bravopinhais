from pathlib import Path
import re

MIGRATIONS = Path(__file__).resolve().parents[2] / "supabase" / "migrations"
MIGRATION = MIGRATIONS / "20261128000700_bravo_shadow_google_identities.sql"


def test_google_identity_migration_is_persistent_and_one_to_one():
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    assert "create table if not exists bravo_shadow.google_identities" in sql
    assert "user_id text primary key" in sql
    assert "references bravo_shadow.usuarios (id)" in sql
    assert "unique (issuer, subject)" in sql
    assert "issuer = 'https://accounts.google.com'" in sql
    assert "verified_email_at_link" in sql
    assert "linked_by text not null" in sql


def test_google_identity_migration_is_fail_closed_and_does_not_grant_access():
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    assert "enable row level security" in sql
    assert "force row level security" in sql
    assert "revoke all on table bravo_shadow.google_identities" in sql
    assert not re.search(r"^\s*grant\s", sql, re.MULTILINE)
    assert not re.search(r"^\s*create\s+policy\s", sql, re.MULTILINE)
    assert not re.search(r"\binsert\s+into\s+bravo_shadow\.google_identities\b", sql)
    assert "a api ainda não consulta esta tabela" in sql
