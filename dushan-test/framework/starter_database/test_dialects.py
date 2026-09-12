import asyncio
from contextlib import suppress

import pytest
from conftest import TARGETS
from pydantic import SecretStr
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import create_async_engine

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
    [target for target in TARGETS if target["name"] == "dameng"],
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
