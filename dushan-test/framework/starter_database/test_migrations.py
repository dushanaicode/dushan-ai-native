import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import column, inspect, select, text
from sqlalchemy import table as sql_table
from sqlalchemy.ext.asyncio import create_async_engine

from framework.starter_database.exception.database_error_codes import DatabaseErrorCodes
from framework.starter_database.exception.database_exception import DatabaseException
from framework.starter_database.migration.migration_runner import MigrationRunner


def migration_versions(path, table):
    path.mkdir()
    (path / "first.py").write_text(
        "from alembic import op\n"
        "from sqlalchemy import Column, Integer, String\n"
        "revision = 'first'\ndown_revision = None\n"
        "def upgrade():\n"
        f"    op.create_table('{table}', Column('id', Integer, primary_key=True), "
        "Column('value', String(32)))\n"
        "def downgrade():\n"
        f"    op.drop_table('{table}')\n",
        encoding="utf-8",
    )
    (path / "second.py").write_text(
        "from alembic import op\n"
        "from sqlalchemy import Column, Integer, String, column, table\n"
        "revision = 'second'\ndown_revision = 'first'\n"
        "def upgrade():\n"
        f"    op.add_column('{table}', Column('number', Integer))\n"
        f"    target = table('{table}', column('id', Integer), column('value', String), "
        "column('number', Integer))\n"
        "    op.bulk_insert(target, [{'id': 7, 'value': 'migrated', 'number': 9}])\n"
        "def downgrade():\n"
        f"    op.drop_column('{table}', 'number')\n",
        encoding="utf-8",
    )
    return path


async def test_explicit_migrations_track_versions_and_preserve_data(database_settings, tmp_path):
    suffix = uuid4().hex[:12]
    table, version_table = "native_mig_" + suffix, "native_ver_" + suffix
    versions = migration_versions(tmp_path / "versions", table)
    runner = MigrationRunner(
        database_settings, source="primary", versions=versions, version_table=version_table
    )
    control = create_async_engine(database_settings.sources[0].url.get_secret_value())
    migrated = sql_table(table, column("id"), column("value"), column("number"))
    try:
        assert not (await runner.run("current")).strip()
        await runner.run("upgrade", revision="head")
        assert "second" in await runner.run("current")
        await runner.run("upgrade", revision="head")
        async with control.connect() as connection:
            rows = (await connection.execute(select(migrated))).all()
        assert [tuple(row) for row in rows] == [(7, "migrated", 9)]
        (versions / "third.py").write_text(
            "from alembic import op\n"
            "from sqlalchemy import Integer, String, column, table\n"
            "revision = 'third'\ndown_revision = 'second'\n"
            "def upgrade():\n"
            f"    target = table('{table}', column('id', Integer), column('value', String))\n"
            "    op.bulk_insert(target, [{'id': 7, 'value': 'private-migration-parameter'}])\n",
            encoding="utf-8",
        )
        with pytest.raises(DatabaseException) as failure:
            await runner.run("upgrade", revision="head")
        assert failure.value.error_code == DatabaseErrorCodes.UNIQUE_VIOLATION
        assert failure.value.context["phase"] == "migration" and not failure.value.retryable
        assert failure.value.__cause__ is None and failure.value.__context__ is None
        assert "second" in await runner.run("current")
        await runner.run("downgrade", revision="first")
        assert "first" in await runner.run("current")
        async with control.connect() as connection:
            rows = (await connection.execute(select(migrated.c.id, migrated.c.value))).all()
        assert [tuple(row) for row in rows] == [(7, "migrated")]
        await runner.run("downgrade", revision="base")
        async with control.connect() as connection:
            assert not await connection.run_sync(lambda sync: inspect(sync).has_table(table))
    finally:
        async with control.begin() as connection:
            for name in (table, version_table):
                exists = await connection.run_sync(lambda sync: inspect(sync).has_table(name))
                if exists:
                    await connection.execute(text(f"DROP TABLE {name}"))
        await control.dispose()


async def test_offline_migration_never_connects(database_settings, tmp_path, monkeypatch):
    from framework.starter_database.connection.connection_factory import ConnectionFactory

    versions = migration_versions(tmp_path / "offline", "native_offline")

    def forbidden(*args, **kwargs):
        raise AssertionError("离线迁移不得创建数据库连接")

    monkeypatch.setattr(ConnectionFactory, "create", forbidden)
    runner = MigrationRunner(database_settings, source="primary", versions=versions)
    sql = await runner.run("upgrade", revision="head", sql=True)
    assert "CREATE TABLE native_offline" in sql
    assert "alembic_version" in sql
    assert database_settings.sources[0].url.get_secret_value() not in sql


async def test_replica_cannot_be_migration_target(database_settings, tmp_path):
    replica = database_settings.sources[0].model_copy(update={"name": "replica", "role": "replica"})
    settings = database_settings.model_copy(
        update={"sources": (*database_settings.sources, replica)}
    )
    with pytest.raises(ValueError):
        MigrationRunner(settings, source="replica", versions=tmp_path)


def test_migration_cli_reports_failure_without_credentials(config_dir, tmp_path):
    root = config_dir()
    versions = migration_versions(tmp_path / "cli_versions", "native_cli")
    process = subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "framework.starter_database.migration",
            "--config-dir",
            str(root),
            "--source",
            "missing",
            "--versions",
            str(versions),
            "upgrade",
            "head",
        ],
        cwd=Path(__file__).resolve().parents[3],
        env={
            **os.environ,
            "PYTHONPATH": str(Path(__file__).resolve().parents[3] / "dushan-admin-backend"),
            "PYTHONUTF8": "1",
            "PYTHONIOENCODING": "utf-8",
        },
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
    )
    assert process.returncode == 1
    assert "数据库迁移失败" in process.stderr
    assert "Traceback" not in process.stderr
