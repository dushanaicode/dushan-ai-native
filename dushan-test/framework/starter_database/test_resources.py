import asyncio

import pytest
from pydantic import SecretStr
from sqlalchemy import select

from framework.starter_database.config.database_pool_settings import DatabasePoolSettings
from framework.starter_database.connection.connection_factory import ConnectionFactory
from framework.starter_database.exception.database_exception import DatabaseException
from framework.starter_database.session.managed_async_session import ManagedAsyncSession
from framework.starter_database.session.session_provider import SessionProvider


async def test_named_source_replacement_does_not_wait_on_callers_old_lease(database_case):
    database, Item, mapper = database_case
    source = database.settings.sources[0].model_copy(update={"name": "reporting", "role": "named"})
    assert await database.replace_sources([source]) == 2
    old_entry = database._registry.entries["reporting"]
    changed_pool = DatabasePoolSettings.model_validate(
        {**database.settings.pool.model_dump(), "size": 2}
    )
    async with database.read_session(source="reporting") as session:
        await session.execute(select(Item))
        revision = await asyncio.wait_for(
            database.replace_sources([source.model_copy(update={"pool": changed_pool})]), 2
        )
        assert revision == 3 and old_entry.retired and old_entry.leases == 1
        assert database.get_metrics()["retiring"] == 1
        assert database._registry.entries["reporting"] is not old_entry
        await session.execute(select(Item))
    await asyncio.gather(*tuple(database._registry._retirement_tasks))
    assert database.get_metrics()["retiring"] == 0
    assert await database.replace_sources([]) == 4


async def test_dynamic_preflight_and_unchanged_refresh_do_not_publish(database_case):
    database, Item, mapper = database_case
    source = database.settings.sources[0].model_copy(update={"name": "reporting", "role": "named"})
    assert await database.replace_sources([source], preflight=True) == 1
    assert "reporting" not in database.get_metrics()["pools"]
    await database.replace_sources([source])
    assert await database.replace_sources([source]) == 2
    assert await database.replace_sources([source], preflight=True) == 2
    with pytest.raises(ValueError):
        await database.replace_sources([source, source])
    assert database.get_metrics()["revision"] == 2


async def test_failed_candidate_cleans_created_engines_and_preserves_published_snapshot(
    database_case, monkeypatch
):
    database, Item, mapper = database_case
    source = database.settings.sources[0].model_copy(update={"name": "candidate", "role": "named"})
    invalid = source.model_copy(
        update={"name": "invalid", "url": SecretStr("missingdialect+driver://localhost/test")}
    )
    disposed = []
    from sqlalchemy.ext.asyncio import AsyncEngine

    original = AsyncEngine.dispose

    async def dispose(engine, *args, **kwargs):
        disposed.append(engine)
        return await original(engine, *args, **kwargs)

    monkeypatch.setattr(AsyncEngine, "dispose", dispose)
    with pytest.raises(Exception, match="dialect"):
        await database.replace_sources([source, invalid])
    assert len(disposed) == 1
    assert database.get_metrics()["revision"] == 1
    assert set(database.get_metrics()["pools"]) == {"primary"}
    assert await mapper.count() == 0


async def test_partial_startup_cleans_engine_when_next_creation_fails(
    database_settings, monkeypatch
):
    source = database_settings.sources[0]
    replica = source.model_copy(update={"name": "replica", "role": "replica"})
    settings = database_settings.model_copy(update={"sources": (source, replica)})
    database = SessionProvider(settings)
    created = []
    disposed = []
    original_create = ConnectionFactory.create
    from sqlalchemy.ext.asyncio import AsyncEngine

    original_dispose = AsyncEngine.dispose

    def create(definition, config):
        if created:
            raise ValueError("second engine")
        engine = original_create(definition, config)
        created.append(engine)
        return engine

    async def dispose(engine, *args, **kwargs):
        disposed.append(engine)
        return await original_dispose(engine, *args, **kwargs)

    monkeypatch.setattr(ConnectionFactory, "create", create)
    monkeypatch.setattr(AsyncEngine, "dispose", dispose)
    with pytest.raises(ValueError, match="second engine"):
        async with database.lifespan():
            pytest.fail("should not be ready")
    assert disposed == created and not database.is_ready


async def test_repeated_cancel_waits_for_actual_session_close(database_case, monkeypatch):
    database, Item, mapper = database_case
    written = asyncio.Event()
    closing = asyncio.Event()
    release = asyncio.Event()
    original = ManagedAsyncSession.close

    async def slow_close(session):
        closing.set()
        await release.wait()
        await original(session)

    monkeypatch.setattr(ManagedAsyncSession, "close", slow_close)

    async def work():
        async with database.transaction():
            await mapper.insert(Item(value="cancelled"))
            written.set()
            await asyncio.Event().wait()

    task = asyncio.create_task(work())
    await written.wait()
    task.cancel()
    await closing.wait()
    try:
        task.cancel()
        await asyncio.sleep(0)
        assert not task.done()
        assert database.get_metrics()["pools"]["primary"]["leases"] == 1
    finally:
        release.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert await mapper.count() == 0


async def test_close_waits_for_required_callback_and_rejects_new_operations(database_case):
    database, Item, mapper = database_case
    started = asyncio.Event()
    release = asyncio.Event()

    async def callback():
        started.set()
        await release.wait()
        await mapper.insert(Item(value="callback-during-drain"))

    async def work():
        async with database.transaction():
            database.after_commit(callback)

    task = asyncio.create_task(work())
    await started.wait()
    close = asyncio.create_task(database.close())
    while not database._transactions._draining:
        await asyncio.sleep(0)
    try:
        assert not close.done()
        with pytest.raises(DatabaseException):
            await mapper.count()
    finally:
        release.set()
    await asyncio.wait_for(asyncio.gather(task, close), 3)
    assert not database.is_ready and not database.get_metrics()["pools"]


async def test_background_callback_is_reserved_before_task_starts(database_case):
    database, Item, mapper = database_case
    completed = []

    async def callback():
        await mapper.insert(Item(value="background"))
        completed.append(True)

    database.after_commit(callback, required=False)
    await database.close()
    assert completed == [True]
    assert database.get_metrics()["after_commit"][-1].success


async def test_self_close_is_rejected_without_hanging(database_case):
    database, Item, mapper = database_case
    async with database.transaction():
        with pytest.raises(RuntimeError, match="自身"):
            await database.close()
        await mapper.insert(Item(value="still-active"))
    assert await mapper.count() == 1


async def test_required_callback_cannot_close_its_own_database(database_case):
    database, Item, mapper = database_case

    async def callback():
        with pytest.raises(RuntimeError, match="自身"):
            await database.close()

    async with database.transaction():
        database.after_commit(callback)
    assert database.is_ready


@pytest.mark.parametrize("strategy", ["round_robin", "random", "weighted", "least_connections"])
async def test_replica_routing_and_write_stickiness(database_case, database_settings, strategy):
    _, Item, _ = database_case
    primary = database_settings.sources[0]
    replicas = [
        primary.model_copy(update={"name": name, "role": "replica"})
        for name in ("read_a", "read_b")
    ]
    database = SessionProvider(
        database_settings.model_copy(
            update={"sources": (primary, *replicas), "replica_strategy": strategy}
        )
    )
    async with database.lifespan():
        with database.scope():
            async with database.read_session() as first:
                assert (
                    sum(
                        database.get_metrics()["pools"][name]["leases"]
                        for name in ("read_a", "read_b")
                    )
                    == 1
                )
                await first.execute(select(Item))
                if strategy == "least_connections":
                    async with database.read_session() as second:
                        assert database.get_metrics()["pools"]["read_a"]["leases"] == 1
                        assert database.get_metrics()["pools"]["read_b"]["leases"] == 1
                        await second.execute(select(Item))
            async with database.transaction():
                pass
            async with database.read_session():
                assert database.get_metrics()["pools"]["primary"]["leases"] == 1
        with database.scope():
            async with database.read_session():
                assert database.get_metrics()["pools"]["primary"]["leases"] == 0


async def test_raw_access_is_forbidden_in_loop_callback_without_task(database_case):
    database, Item, _ = database_case
    async with database.read_session() as session:
        result = await session.execute(select(Item))
        completed = asyncio.get_running_loop().create_future()

        def access():
            try:
                _ = result.raw
            except DatabaseException:
                completed.set_result(True)
            else:
                completed.set_result(False)

        asyncio.get_running_loop().call_soon(access)
        assert await completed
