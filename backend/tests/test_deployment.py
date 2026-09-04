import os
import shutil
import subprocess
import tarfile
from pathlib import Path

import pytest
import yaml
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


EXPECTED_TABLES = {
    "admin_users",
    "admin_sessions",
    "persons",
    "relationships",
    "sources",
    "source_links",
    "change_drafts",
    "audit_logs",
}


def usable_bash() -> str | None:
    discovered = shutil.which("bash")
    candidates = [] if discovered is None else [Path(discovered)]
    git = shutil.which("git")
    if git:
        candidates.append(Path(git).parent.parent / "bin" / "bash.exe")
    candidates.append(Path("D:/C/msys2/usr/bin/bash.exe"))
    for candidate in candidates:
        if candidate.is_file() and "system32" not in str(candidate).lower():
            return str(candidate)
    return None


def bash_path(path: Path) -> str:
    resolved = path.resolve().as_posix()
    if os.name == "nt" and len(resolved) > 2 and resolved[1] == ":":
        return f"/{resolved[0].lower()}{resolved[2:]}"
    return resolved


def test_initial_migration_creates_all_tables(tmp_path):
    database = tmp_path / "migration.db"
    config_path = Path("backend/alembic.ini")
    assert config_path.exists(), "Alembic 配置尚未实现"
    config = Config(str(config_path))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database}")

    command.upgrade(config, "head")

    tables = set(inspect(create_engine(f"sqlite:///{database}")).get_table_names())
    assert EXPECTED_TABLES <= tables


def test_relationship_inference_migration_preserves_old_siblings(tmp_path):
    database = tmp_path / "migration.db"
    config = Config("backend/alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database}")

    command.upgrade(config, "0001_initial")
    engine = create_engine(f"sqlite:///{database}")
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO persons (id, name, gender, verification_status, "
                "created_at, updated_at) VALUES "
                "('p1', '贺志豪', 'male', 'unverified', CURRENT_TIMESTAMP, "
                "CURRENT_TIMESTAMP), "
                "('p2', '贺志兰', 'female', 'unverified', CURRENT_TIMESTAMP, "
                "CURRENT_TIMESTAMP)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO relationships (id, kind, person_id, relative_id, "
                "verification_status, created_at) VALUES "
                "('r1', 'sibling', 'p1', 'p2', 'unverified', CURRENT_TIMESTAMP)"
            )
        )

    command.upgrade(config, "head")

    columns = {item["name"] for item in inspect(engine).get_columns("persons")}
    with engine.connect() as connection:
        sibling_type = connection.scalar(
            text("SELECT sibling_type FROM relationships WHERE id='r1'")
        )
    assert {
        "birth_place",
        "courtesy_name",
        "art_name",
        "aliases",
        "generation_name",
        "family_rank",
        "occupation",
    } <= columns
    assert sibling_type == "unknown"


def test_backup_contains_database_dump_and_private_archives(tmp_path):
    bash = usable_bash()
    if bash is None:
        pytest.skip("当前环境没有 bash")

    archive_dir = tmp_path / "archives"
    backup_dir = tmp_path / "backups"
    archive_dir.mkdir()
    (archive_dir / "family-record.pdf").write_bytes(b"private archive")
    fake_pg_dump = tmp_path / "fake-pg-dump.sh"
    fake_pg_dump.write_text("#!/usr/bin/env bash\nprintf 'fake database dump\\n'\n", encoding="utf-8")
    fake_pg_dump.chmod(0o755)

    environment = os.environ.copy()
    environment.update(
        {
            "DATABASE_URL": "postgresql://example.invalid/guiyuan",
            "ARCHIVE_DIR": bash_path(archive_dir),
            "BACKUP_DIR": bash_path(backup_dir),
            "PG_DUMP_BIN": bash_path(fake_pg_dump),
            "ENV_FILE": bash_path(tmp_path / "missing.env"),
        }
    )
    script = Path("scripts/backup.sh")
    assert script.exists(), "备份脚本尚未实现"

    subprocess.run([bash, script.as_posix()], check=True, env=environment)

    backups = list(backup_dir.glob("guiyuan-backup-*.tar.gz"))
    assert len(backups) == 1
    with tarfile.open(backups[0]) as bundle:
        names = set(bundle.getnames())
        assert "database.sql" in names
        assert "archives/family-record.pdf" in names


def test_restore_imports_database_dump_and_private_archives(tmp_path):
    bash = usable_bash()
    if bash is None:
        pytest.skip("当前环境没有 bash")

    bundle = tmp_path / "backup.tar.gz"
    bundle_contents = tmp_path / "bundle"
    (bundle_contents / "archives").mkdir(parents=True)
    (bundle_contents / "database.sql").write_text("restored database\n", encoding="utf-8")
    (bundle_contents / "archives" / "record.txt").write_text("restored archive", encoding="utf-8")
    with tarfile.open(bundle, "w:gz") as archive:
        archive.add(bundle_contents / "database.sql", arcname="database.sql")
        archive.add(bundle_contents / "archives", arcname="archives")

    archive_dir = tmp_path / "restored-archives"
    captured_sql = tmp_path / "captured.sql"
    fake_psql = tmp_path / "fake-psql.sh"
    fake_psql.write_text('#!/usr/bin/env bash\ncat > "$CAPTURED_SQL"\n', encoding="utf-8")
    fake_psql.chmod(0o755)
    environment = os.environ.copy()
    environment.update(
        {
            "DATABASE_URL": "postgresql://example.invalid/guiyuan",
            "ARCHIVE_DIR": bash_path(archive_dir),
            "PSQL_BIN": bash_path(fake_psql),
            "CAPTURED_SQL": bash_path(captured_sql),
        }
    )

    subprocess.run(
        [bash, "scripts/restore.sh", bash_path(bundle)],
        check=True,
        env=environment,
    )

    assert captured_sql.read_text(encoding="utf-8") == "restored database\n"
    assert (archive_dir / "record.txt").read_text(encoding="utf-8") == "restored archive"


def test_compose_keeps_data_private_and_health_checked():
    compose_path = Path("compose.yaml")
    assert compose_path.exists(), "Compose 配置尚未实现"
    compose = yaml.safe_load(compose_path.read_text(encoding="utf-8"))

    assert set(compose["services"]) == {"proxy", "api", "db"}
    assert "ports" not in compose["services"]["db"]
    assert "healthcheck" in compose["services"]["api"]
    assert "healthcheck" in compose["services"]["db"]
    assert "db_data" in compose["volumes"]
    assert "archives" in compose["volumes"]
    assert any("archives:/app/data/archives" in item for item in compose["services"]["api"]["volumes"])
