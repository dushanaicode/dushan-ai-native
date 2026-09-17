import json
import os
from pathlib import Path
from uuid import uuid4

import pymysql
import pytest
import pytest_asyncio
import yaml
from httpx import ASGITransport, AsyncClient
from pymysql.constants import CLIENT
from redis import Redis

from fixtures.config_factory import ConfigFactory
from fixtures.http_route_coverage import HttpRouteCoverage


@pytest.fixture(scope="module")
def system_database():
    root = Path(__file__).resolve().parents[2]
    resource_value = os.environ.get("DUSHAN_SYSTEM_RESOURCES")
    if resource_value is None:
        pytest.skip("需要本轮独立 MySQL/Redis 资源清单 DUSHAN_SYSTEM_RESOURCES")
    resource_path = Path(resource_value)
    resources = json.loads(resource_path.read_text(encoding="utf-8"))
    temporary = (root / "Temp").resolve()
    assert temporary.is_relative_to(root.resolve())
    assert Path(resources["mysql_datadir"]).resolve().is_relative_to(temporary)
    expected_redis_root = "/mnt/" + root.drive[0].lower() + root.as_posix()[2:] + "/Temp/"
    assert resources["redis_dir"].startswith(expected_redis_root)
    connection = pymysql.connect(
        host="127.0.0.1",
        port=resources["mysql_port"],
        user="root",
        password="",
        autocommit=True,
        charset="utf8mb4",
        client_flag=CLIENT.MULTI_STATEMENTS,
    )
    name = "system_" + uuid4().hex
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT @@datadir, @@port")
            data_dir, port = cursor.fetchone()
            assert Path(data_dir).resolve() == Path(resources["mysql_datadir"]).resolve()
            assert port == resources["mysql_port"]
            cursor.execute(
                f"CREATE DATABASE `{name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
            cursor.execute(f"USE `{name}`")
            for sql_file in sorted((root / "dushan-admin-backend/sql/mysql/system").glob("*.sql")):
                cursor.execute(sql_file.read_text(encoding="utf-8"))
                while cursor.nextset():
                    pass
        redis = Redis(host="127.0.0.1", port=resources["redis_port"], decode_responses=True)
        assert redis.config_get("dir")["dir"] == resources["redis_dir"]
        redis.flushdb()
        redis.close()
        yield resources, name, connection
    finally:
        with connection.cursor() as cursor:
            cursor.execute(f"DROP DATABASE IF EXISTS `{name}`")
        connection.close()


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def system_app(system_database, tmp_path_factory):
    from server.starter_server import create_app

    resources, name, _ = system_database
    values = ConfigFactory.values()
    folder = tmp_path_factory.mktemp("system-config")
    values["modules"]["enabled"] = ["framework", "system"]
    values["server"]["reload"] = False
    values["log"]["enable_file_overall"] = False
    values["log"]["console_level"] = "WARNING"
    models = values["config"]["models"]
    models["database"].update(
        enabled=True,
        health_check_enabled=False,
        id_strategy="snowflake",
        snowflake_machine_id=913,
        sources=[
            dict(
                name="primary",
                url=f"mysql+aiomysql://root@127.0.0.1:{resources['mysql_port']}/{name}?charset=utf8mb4",
                role="primary",
                weight=100,
                pool=None,
                tls=None,
            )
        ],
    )
    models["cache"].update(enabled=True, host="127.0.0.1", port=resources["redis_port"])
    models["security"].update(enabled=True, permission_cache_enabled=True, bizlog_enabled=True)
    values["expression"]["enabled"] = True
    models["data_permission"].update(enabled=True, cache_enabled=True)
    models["protection"]["enabled"] = True
    models["system"].update(
        user_register_enabled=True,
        workload_credential=uuid4().hex + uuid4().hex,
        message_signing_key=uuid4().hex + uuid4().hex,
        refresh_cookie_secure=False,
        allowed_origins=["http://testserver"],
    )
    values["page"]["fetch_all_enabled"] = True
    (folder / "application.yaml").write_text(
        yaml.safe_dump(values, allow_unicode=True), encoding="utf-8"
    )
    app = create_app(base_dir=folder, app_env="dev", environ={})
    app.add_middleware(HttpRouteCoverage)
    async with app.router.lifespan_context(app):
        HttpRouteCoverage.register(app)
        yield app


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def admin_client(system_app):
    async with AsyncClient(
        transport=ASGITransport(app=system_app), base_url="http://testserver"
    ) as client:
        result = (
            await client.post(
                "/admin-api/system/auth/login", json={"username": "admin", "password": "admin123"}
            )
        ).json()
        assert result["code"] == 0, result
        client.headers["Authorization"] = "Bearer " + result["data"]["accessToken"]
        yield client
