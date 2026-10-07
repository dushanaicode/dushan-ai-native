import json
import os
from pathlib import Path
from uuid import uuid4

import pymysql
import pytest
from pymysql.constants import CLIENT


def test_generated_mysql_schema_and_all_seeds():
    """在专用临时库执行全部发布 SQL，核对字典契约及生成列约束。"""
    resource_file = os.environ.get("DUSHAN_SYSTEM_RESOURCES")
    if resource_file is None:
        pytest.skip("需要本轮独立 MySQL/Redis 资源清单 DUSHAN_SYSTEM_RESOURCES")
    root = Path(__file__).resolve().parents[3]
    resources = json.loads(Path(resource_file).read_text(encoding="utf-8-sig"))
    name = os.environ.get("DUSHAN_TEST_DATABASE_PREFIX", "schema_export_") + uuid4().hex
    connection = pymysql.connect(
        host="127.0.0.1",
        port=resources["mysql_port"],
        user="root",
        password="",
        charset="utf8mb4",
        autocommit=True,
        client_flag=CLIENT.MULTI_STATEMENTS,
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT @@datadir, @@port")
            data_dir, port = cursor.fetchone()
            assert Path(data_dir).resolve() == Path(resources["mysql_datadir"]).resolve()
            assert Path(data_dir).resolve().is_relative_to(root / "Temp")
            assert port == resources["mysql_port"]
            cursor.execute(
                f"CREATE DATABASE `{name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
            try:
                cursor.execute(f"USE `{name}`")
                for module in ("system", "infra"):
                    for source in sorted(
                        (root / "dushan-admin-backend/sql/mysql" / module).glob("*.sql")
                    ):
                        cursor.execute(source.read_text(encoding="utf-8"))
                        while cursor.nextset():
                            pass
                cursor.execute(
                    "SELECT COUNT(*) FROM system_dict_type WHERE type='system_menu_type'"
                )
                assert cursor.fetchone()[0] == 0
                cursor.execute(
                    "SELECT COUNT(*) FROM system_dict_data WHERE dict_type='system_menu_type'"
                )
                assert cursor.fetchone()[0] == 0
                cursor.execute("SELECT COUNT(*) FROM system_dict_data WHERE tag_style IS NOT NULL")
                assert cursor.fetchone()[0] == 0
                cursor.execute("SELECT COUNT(*) FROM system_dict_data")
                assert cursor.fetchone()[0] > 0
                cursor.execute(
                    "SELECT COUNT(*) FROM information_schema.columns "
                    "WHERE table_schema=%s AND column_name IN "
                    "('id','creator','create_time','updater','update_time','deleted','tenant_id') "
                    "AND column_comment=''",
                    (name,),
                )
                assert cursor.fetchone()[0] == 0
                cursor.execute(
                    "SELECT id, code FROM system_post WHERE deleted=0 ORDER BY id LIMIT 1"
                )
                post_id, code = cursor.fetchone()
                cursor.execute("UPDATE system_post SET deleted=1 WHERE id=%s", (post_id,))
                cursor.execute("SELECT active_key FROM system_post WHERE id=%s", (post_id,))
                assert cursor.fetchone()[0] is None
                cursor.execute(
                    "INSERT INTO system_post (id,code,name,sort,status,tenant_id,creator,"
                    "create_time,updater,update_time,deleted) "
                    "SELECT id+100000,code,name,sort,status,tenant_id,creator,create_time,"
                    "updater,update_time,0 FROM system_post WHERE id=%s",
                    (post_id,),
                )
                cursor.execute(
                    "SELECT active_key FROM system_post WHERE code=%s AND deleted=0", (code,)
                )
                assert cursor.fetchone()[0] == 1
                with pytest.raises(pymysql.err.IntegrityError, match="Duplicate entry"):
                    cursor.execute("UPDATE system_post SET deleted=0 WHERE id=%s", (post_id,))
            finally:
                cursor.execute(f"DROP DATABASE `{name}`")
    finally:
        connection.close()
