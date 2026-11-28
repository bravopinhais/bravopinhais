from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
SUPABASE = ROOT / "supabase"
MIGRATIONS = SUPABASE / "migrations"


def test_supabase_cli_project_config_is_local_only():
    config = (SUPABASE / "config.toml").read_text()
    assert 'project_id = "bravo-shadow-local"' in config
    assert "[remotes." not in config
    assert "SUPABASE_DB_PASSWORD" not in config
    assert "SUPABASE_ACCESS_TOKEN" not in config


def test_migration_filenames_match_cli_timestamp_convention():
    files = sorted(path.name for path in MIGRATIONS.glob("*.sql"))
    assert len(files) == 7
    assert all(re.fullmatch(r"\d{14}_[a-z0-9_]+\.sql", name) for name in files)
    versions = [name[:14] for name in files]
    assert versions == sorted(versions)
    assert len(versions) == len(set(versions))


def test_migration_history_has_no_runtime_grant_statements():
    for path in MIGRATIONS.glob("*.sql"):
        sql = path.read_text()
        assert not re.search(r"^\s*grant\s", sql, re.IGNORECASE | re.MULTILINE)
