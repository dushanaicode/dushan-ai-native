import asyncio
from contextlib import suppress
from uuid import uuid4

import pytest
from pydantic import SecretStr
from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    MetaData,
    Table,
    and_,
    func,
    insert,
    select,
    text,
    true,
)
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from fixtures.database_fixtures import TARGETS
from framework.starter_database.session.session_provider import SessionProvider


@pytest.mark.parametrize(
    "database_settings",
    [target for target in TARGETS if target["name"] == "oceanbase"],
    indirect=True,
    ids=lambda target: target["name"],
)
async def test_mysql_protocol_autocommit_must_be_off(database_settings):
    source = database_settings.sources[0]
    url = source.url.get_secret_value()
    unsafe_source = source.model_copy(
        update={"url": SecretStr(url.replace("oceanbase+aiomysql:", "mysql+aiomysql:", 1))}
    )
    database = SessionProvider(database_settings.model_copy(update={"sources": (unsafe_source,)}))
    with pytest.raises(ValueError, match="自动提交"):
        async with database.lifespan():
            pytest.fail("generic driver must not publish an unsafe transaction provider")


@pytest.mark.parametrize(
    "database_settings",
    [target for target in TARGETS if target["name"] == "dm"],
    indirect=True,
    ids=lambda target: target["name"],
)
async def test_dm_async_connect_does_not_block_event_loop(database_settings, monkeypatch):
    source = database_settings.sources[0]
    import threading

    import dmPython

    from framework.starter_database.connection.connection_factory import ConnectionFactory

    original = dmPython.connect
    entered = threading.Event()
    release = threading.Event()

    def delayed(*args, **kwargs):
        assert kwargs["local_code"] == dmPython.PG_UTF8
        entered.set()
        if not release.wait(3):
            raise TimeoutError("event loop could not release blocking driver connect")
        return original(*args, **kwargs)

    monkeypatch.setattr(dmPython, "connect", delayed)
    engine = ConnectionFactory.create(source, database_settings)

    async def connect():
        async with engine.connect() as connection:
            return await connection.scalar(text("SELECT 1"))

    task = asyncio.create_task(connect())
    try:
        async with asyncio.timeout(1):
            while not entered.is_set():
                await asyncio.sleep(0.01)
        release.set()
        assert await task == 1
    finally:
        release.set()
        with suppress(Exception):
            await task
        await engine.dispose()


@pytest.mark.parametrize(
    "database_settings",
    [target for target in TARGETS if target["name"] == "dm"],
    indirect=True,
    ids=lambda target: target["name"],
)
async def test_dm_forces_utf8_and_url_path_selects_schema(database_settings):
    """DPI 始终使用 UTF-8；无 URL 路径时使用登录用户模式，路径指定模式。"""
    import dmPython

    url = make_url(database_settings.sources[0].url.get_secret_value())
    schema_name = "NATIVE_SCHEMA_" + uuid4().hex[:16].upper()
    admin = create_async_engine(url.set(database=None), isolation_level="AUTOCOMMIT")
    created = False
    try:
        async with admin.connect() as connection:
            await connection.exec_driver_sql(
                f'CREATE USER "{schema_name}" IDENTIFIED BY "Schema@{uuid4().hex}"'
            )
        created = True
        for explicit_schema in (False, True):
            engine = create_async_engine(
                url.set(database=schema_name if explicit_schema else None),
                connect_args={"local_code": dmPython.PG_SQL_ASCII},
            )
            try:
                async with engine.connect() as connection:
                    raw = (await connection.get_raw_connection()).driver_connection.raw
                    assert raw.local_code == dmPython.PG_UTF8
                    expected = (
                        schema_name
                        if explicit_schema
                        else await connection.scalar(text("SELECT USER FROM DUAL"))
                    )
                    assert raw.current_schema == expected
                    value = "中文😀"
                    assert await connection.scalar(text("SELECT :value"), {"value": value}) == value
            finally:
                await engine.dispose()
    finally:
        try:
            if created:
                async with admin.connect() as connection:
                    await connection.exec_driver_sql(f'DROP USER "{schema_name}" CASCADE')
        finally:
            await admin.dispose()


@pytest.mark.parametrize(
    "database_settings",
    [target for target in TARGETS if target["name"] == "dm"],
    indirect=True,
    ids=lambda target: target["name"],
)
async def test_dm_boolean_is_keeps_null_semantics(database_settings):
    """布尔 IS/IS NOT 支持真、假和 NULL，普通 IS NULL 继续使用原生语法。"""
    table = Table(
        "boolean_flags_" + uuid4().hex[:16],
        MetaData(),
        Column("id", Integer, primary_key=True, autoincrement=False),
        Column("flag", Boolean),
    )
    engine = create_async_engine(database_settings.sources[0].url.get_secret_value())
    created = False
    try:
        async with engine.begin() as connection:
            await connection.run_sync(table.create)
        created = True
        async with engine.begin() as connection:
            await connection.execute(
                insert(table),
                [{"id": 1, "flag": True}, {"id": 2, "flag": False}, {"id": 3, "flag": None}],
            )
            for predicate, expected in (
                (table.c.flag.is_(True), [1]),
                (table.c.flag.is_(False), [2]),
                (table.c.flag.is_not(True), [2, 3]),
                (table.c.flag.is_not(False), [1, 3]),
                (table.c.flag.is_(None), [3]),
                (table.c.flag.is_not(None), [1, 2]),
                ((table.c.flag == true()).is_(True), [1]),
                ((table.c.flag == true()).is_(False), [2]),
                ((table.c.flag == true()).is_not(True), [2, 3]),
                ((table.c.flag == true()).is_not(False), [1, 3]),
                (and_(table.c.id > 0, table.c.flag == true()).is_not(True), [2, 3]),
                ((~table.c.flag).is_(True), [2]),
                ((~table.c.flag).is_(False), [1]),
                ((~table.c.flag).is_not(True), [1, 3]),
                ((~table.c.flag).is_not(False), [2, 3]),
            ):
                statement = select(table.c.id).where(predicate).order_by(table.c.id)
                assert (await connection.scalars(statement)).all() == expected
    finally:
        try:
            if created:
                async with engine.begin() as connection:
                    await connection.run_sync(table.drop)
        finally:
            await engine.dispose()


@pytest.mark.parametrize(
    "database_settings",
    [target for target in TARGETS if target["name"] == "mysql"],
    indirect=True,
    ids=lambda target: target["name"],
)
async def test_mysql_pre_ping_replaces_actual_disconnected_pool_connection(database_settings):
    database = SessionProvider(database_settings)
    control = create_async_engine(database_settings.sources[0].url.get_secret_value())
    try:
        async with database.lifespan():
            async with database.read_session() as session:
                original = await session.scalar(select(func.connection_id()))
            async with control.connect() as connection:
                # ID 来自专用实例当前连接，命令仅关闭本测试刚归还的池连接。
                await connection.execute(text(f"KILL CONNECTION {int(original)}"))
            async with database.read_session() as session:
                replacement = await session.scalar(select(func.connection_id()))
            assert replacement != original
            assert database.get_metrics()["pools"]["primary"]["leases"] == 0
    finally:
        await control.dispose()
