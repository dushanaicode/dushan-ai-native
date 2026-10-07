import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

from framework.starter_database.ddl.ddl_cli import DdlCli
from framework.starter_database.ddl.ddl_exporter import DdlExporter
from framework.starter_database.model.base import Base


class TestSqlDialectSeeds:
    ROOT = Path(__file__).resolve().parents[3]
    SQL_ROOT = ROOT / "dushan-admin-backend/sql"
    TOOL = ROOT / "dushan-test/tools/sql-dialects/seed_sql_converter.py"
    DIALECTS = ("mysql", "tidb", "oceanbase", "postgresql", "opengauss", "kingbase", "dm")
    FILES = (
        "system/00_module_system.sql",
        "system/01_system_data.sql",
        "system/02_system_dict_data.sql",
        "system/03_system_menu_data_system.sql",
        "infra/00_module_infra.sql",
        "infra/01_infra_data.sql",
        "infra/02_system_menu_data_infra.sql",
        "infra/03_infra_mq_data.sql",
    )

    @staticmethod
    @pytest.fixture(scope="class")
    def converter():
        """加载独立 CLI 工具和业务模型。"""
        spec = importlib.util.spec_from_file_location(
            "seed_sql_converter", TestSqlDialectSeeds.TOOL
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for name in ("system", "infra"):
            DdlCli._import_models(f"module_{name}")
        return module.SeedSqlConverter

    @staticmethod
    @pytest.mark.parametrize("hash_seed", ["1", "527"])
    def test_generated_seeds_match_committed_files(tmp_path, hash_seed):
        """不同哈希种子的独立进程都必须生成与发布文件逐字节相同的种子。"""
        environment = {
            **os.environ,
            "PYTHONPATH": str(TestSqlDialectSeeds.ROOT / "dushan-admin-backend"),
            "PYTHONHASHSEED": hash_seed,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONIOENCODING": "utf-8",
        }
        subprocess.run(
            [
                sys.executable,
                "-B",
                str(TestSqlDialectSeeds.TOOL),
                "--sql-root",
                str(TestSqlDialectSeeds.SQL_ROOT),
                "--output-root",
                str(tmp_path),
            ],
            env=environment,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        generated = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*.sql"))
        committed = sorted(
            path.relative_to(TestSqlDialectSeeds.SQL_ROOT)
            for dialect in TestSqlDialectSeeds.DIALECTS
            if dialect != "mysql"
            for path in (TestSqlDialectSeeds.SQL_ROOT / dialect).rglob("*.sql")
            if not path.name.startswith("00_")
        )
        assert generated == committed
        assert len(generated) == 36
        for relative in generated:
            assert (tmp_path / relative).read_bytes() == (
                TestSqlDialectSeeds.SQL_ROOT / relative
            ).read_bytes(), relative

    @staticmethod
    @pytest.mark.parametrize("dialect", DIALECTS)
    def test_each_database_has_eight_files(dialect):
        """每种数据库均包含独立、完整的八个初始化文件。"""
        directory = TestSqlDialectSeeds.SQL_ROOT / dialect
        assert sorted(
            path.relative_to(directory).as_posix()
            for path in directory.rglob("*")
            if path.is_file()
        ) == sorted(TestSqlDialectSeeds.FILES)

    @staticmethod
    @pytest.mark.parametrize("dialect", DIALECTS)
    @pytest.mark.parametrize("module_name", ["system", "infra"])
    def test_offline_ddl_matches_published_files(tmp_path, dialect, module_name):
        """通过真实 CLI 独立导出每种方言，包含文件头和换行的全部字节必须一致。"""
        output = tmp_path / f"00_module_{module_name}.sql"
        subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "framework.starter_database.ddl",
                "--package",
                f"module_{module_name}",
                "--dialect",
                dialect,
                "--output",
                str(output),
            ],
            env={
                **os.environ,
                "PYTHONPATH": str(TestSqlDialectSeeds.ROOT / "dushan-admin-backend"),
                "PYTHONHASHSEED": "0",
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONIOENCODING": "utf-8",
            },
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        source = (
            TestSqlDialectSeeds.SQL_ROOT / dialect / module_name / f"00_module_{module_name}.sql"
        )
        actual = output.read_bytes()
        assert actual == source.read_bytes()
        assert actual.count(b"CREATE TABLE ") == (35 if module_name == "system" else 19)

    @staticmethod
    def test_opengauss_offline_identity_uses_serial(converter):
        """openGauss 未连接时也按已确认的 PG 9.2 能力导出自增列。"""
        exporter = DdlExporter(Base.metadata, "opengauss")
        ddl = exporter._table(Base.metadata.tables["system_tenant"])
        assert "id BIGSERIAL NOT NULL" in ddl
        assert "GENERATED BY DEFAULT AS IDENTITY" not in ddl

    @staticmethod
    def test_dm_virtual_unique_indexes_preserve_other_dialects(converter):
        """达梦独立唯一索引不改变模型约束及同进程内其他六库的输出。"""
        table = Base.metadata.tables["system_post"]
        others = tuple(name for name in TestSqlDialectSeeds.DIALECTS if name != "dm")
        before = {
            name: DdlExporter(Base.metadata, name).export(title="metadata reuse") for name in others
        }
        dm = DdlExporter(Base.metadata, "dm")._table(table)
        assert "CONSTRAINT uq_system_post_active_0 UNIQUE" not in dm
        assert "CREATE UNIQUE INDEX uq_system_post_active_0 ON system_post (" in dm
        assert (
            "tenant_id, code, active_key, CASE WHEN active_key IS NOT NULL THEN NULL ELSE id END"
        ) in dm
        assert "CONSTRAINT uq_system_post_tenant_id UNIQUE" in dm
        DdlExporter(Base.metadata, "dm").export(title="metadata reuse")
        for name in others:
            assert DdlExporter(Base.metadata, name).export(title="metadata reuse") == before[name]

    @staticmethod
    @pytest.mark.parametrize("dialect", ["postgresql", "dm"])
    def test_string_boolean_identifier_and_time_conversion(converter, dialect):
        """字符串中的 SQL 片段、分号、引号、通配符和反斜杠必须保持原值。"""
        source = r"""
            SET NAMES utf8mb4;
            SET time_zone = '+00:00';
            INSERT IGNORE INTO `infra_file_config` (`id`, `name`, `remark`, `master`, `deleted`, `create_time`)
            VALUES (71, 'O\'Reilly', 'NOW(); `id` b\'0\' 100% a_b C:\\dir', 1, b'0', UTC_TIMESTAMP());
        """
        result = converter.convert(source, dialect, "fixture.sql")
        assert "'O''Reilly'" in result
        assert "'NOW(); `id` b''0'' 100% a_b C:\\dir'" in result
        assert (
            "INSERT INTO infra_file_config (id, name, remark, master, deleted, create_time)"
            in result
        )
        assert "INSERT IGNORE" not in result
        if dialect == "postgresql":
            assert "TRUE, FALSE, (CURRENT_TIMESTAMP AT TIME ZONE 'UTC')" in result
            assert "SET standard_conforming_strings = on;" in result
            assert (
                "SELECT setval(pg_get_serial_sequence('infra_file_config', 'id'), MAX(id), true) "
                "FROM infra_file_config;"
            ) in result
        else:
            assert "1, 0, GETUTCDATE()" in result
            assert "SET IDENTITY_INSERT infra_file_config ON;" in result
            assert "SET IDENTITY_INSERT infra_file_config OFF;" in result

    @staticmethod
    @pytest.mark.parametrize(
        "source",
        [
            "DELETE FROM system_post;",
            "SET time_zone = '+08:00';",
            "INSERT INTO system_post (id) SELECT 1;",
            "INSERT INTO system_post (id) VALUES (ABS(1));",
            "INSERT INTO system_post (name) VALUES ('a' 'b');",
            "INSERT INTO system_post (id, deleted) VALUES (1, 7);",
            "INSERT INTO system_post (id) VALUES (1)",
        ],
    )
    def test_unrecognized_seed_syntax_fails_explicitly(converter, source):
        """源种子超出已支持语法时停止生成，禁止默默遗漏数据或语义。"""
        with pytest.raises(ValueError):
            converter.convert(source, "postgresql", "fixture.sql")
