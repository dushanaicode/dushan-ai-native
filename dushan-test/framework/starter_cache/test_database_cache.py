import json
import os
from uuid import uuid4

import pytest
from sqlalchemy import MetaData, String, select, update
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import mapped_column

from fixtures.cache_fixtures import app_values, redis_values, requires_redis
from fixtures.config_factory import ConfigFactory
from fixtures.starter_steps import StarterSteps
from framework.starter_cache.core.cache_handler import CacheHandler
from framework.starter_cache.core.cache_invalidation_dispatcher import CacheInvalidationDispatcher
from framework.starter_cache.exception.cache_exception import CacheException
from framework.starter_cache.model.cache_entry_invalidation_command import (
    CacheEntryInvalidationCommand,
)
from framework.starter_database.model.base_do import BaseDO
from framework.starter_database.session.session_provider import SessionProvider
from server.starter_server import create_app

# 数据库与缓存的协作语义必须在真实 MySQL 上验证，SQLite 无法代表跨进程提交行为。
MYSQL = next(
    (
        target
        for target in json.loads(os.environ.get("DUSHAN_DATABASE_TEST_URLS", "[]"))
        if target["name"] == "mysql"
    ),
    None,
)

pytestmark = [requires_redis, pytest.mark.skipif(MYSQL is None, reason="需要真实 MySQL 实例")]


def database_values(url: str) -> dict:
    values = ConfigFactory.values()["config"]["models"]["database"]
    values.update(enabled=True, health_check_enabled=False, slow_query_enabled=False)
    values["connect_timeout_seconds"] = 5
    values["sources"] = [
        {"name": "primary", "url": url, "role": "primary", "weight": 100, "pool": None, "tls": None}
    ]
    return values


@pytest.fixture
async def joint_app(config_dir, module_values, key_module, cache_prefix):
    """同时接入真实 MySQL 与真实 Redis 的完整应用。"""
    identifier = uuid4().hex[:16]
    item_type = type(
        "CacheJointItem_" + identifier,
        (BaseDO,),
        {
            "__tablename__": "native_cache_joint_" + identifier,
            "metadata": MetaData(),
            "value": mapped_column(String(64), nullable=True),
        },
    )
    schema = create_async_engine(MYSQL["url"])
    values = app_values(redis_values(), **module_values)
    values["config"]["models"]["database"] = database_values(MYSQL["url"])
    app = create_app(base_dir=config_dir(values), environ={}, steps=StarterSteps.without_tenant())
    created = False
    try:
        async with schema.begin() as connection:
            await connection.run_sync(item_type.__table__.create)
        created = True
        async with app.router.lifespan_context(app):
            yield app, item_type, key_module
    finally:
        try:
            if created:
                async with schema.begin() as connection:
                    await connection.run_sync(item_type.__table__.drop)
        finally:
            await schema.dispose()


def flatten(error: BaseException) -> tuple[list[BaseException], list[str]]:
    """展开嵌套异常组，返回全部叶子异常和链路上出现过的说明文本。"""
    leaves: list[BaseException] = []
    messages: list[str] = [str(error)]
    if isinstance(error, BaseExceptionGroup):
        messages.append(error.message)
        for child in error.exceptions:
            child_leaves, child_messages = flatten(child)
            leaves.extend(child_leaves)
            messages.extend(child_messages)
    else:
        leaves.append(error)
        cause = error.__cause__
        if cause is not None:
            cause_leaves, cause_messages = flatten(cause)
            leaves.extend(cause_leaves)
            messages.extend(cause_messages)
    return leaves, messages


async def load_value(database: SessionProvider, item_type, row_id: int) -> str | None:
    async with database.read_session() as session:
        return await session.scalar(select(item_type.value).where(item_type.id == row_id))


async def insert_row(database: SessionProvider, item_type, value: str) -> int:
    async with database.transaction() as session:
        row = item_type(value=value)
        session.add(row)
        await session.flush()
        return row.id


async def test_invalidation_after_commit_makes_the_next_read_see_committed_data(joint_app):
    app, item_type, keys = joint_app
    context = app.state.application_context
    with context.execution():
        database = context.get_bean(SessionProvider)
        cache = context.get_bean(CacheHandler)
        dispatcher = context.get_bean(CacheInvalidationDispatcher)
        row_id = await insert_row(database, item_type, "旧值")

        cached = await cache.get_or_load(
            keys.TestCacheKeys.ITEM,
            str(row_id),
            lambda: load_value(database, item_type, row_id),
            60,
        )
        assert cached == "旧值"

        command = CacheEntryInvalidationCommand(
            cache_key=keys.TestCacheKeys.ITEM, identifier=str(row_id)
        )
        async with database.transaction() as session:
            await session.execute(
                update(item_type).where(item_type.id == row_id).values(value="新值")
            )
            database.after_commit(lambda: dispatcher.dispatch(command), name="cache-invalidate")

        assert (await cache.get(keys.TestCacheKeys.ITEM, str(row_id))).hit is False
        assert (
            await cache.get_or_load(
                keys.TestCacheKeys.ITEM,
                str(row_id),
                lambda: load_value(database, item_type, row_id),
                60,
            )
            == "新值"
        )
        await cache.delete_all(keys.TestCacheKeys.ITEM)


async def test_rolled_back_transaction_neither_writes_data_nor_invalidates_cache(joint_app):
    app, item_type, keys = joint_app
    context = app.state.application_context
    with context.execution():
        database = context.get_bean(SessionProvider)
        cache = context.get_bean(CacheHandler)
        dispatcher = context.get_bean(CacheInvalidationDispatcher)
        row_id = await insert_row(database, item_type, "原值")
        await cache.set(keys.TestCacheKeys.ITEM, str(row_id), "原值", ttl_seconds=60)

        command = CacheEntryInvalidationCommand(
            cache_key=keys.TestCacheKeys.ITEM, identifier=str(row_id)
        )
        with pytest.raises(RuntimeError):
            async with database.transaction() as session:
                await session.execute(
                    update(item_type).where(item_type.id == row_id).values(value="不该生效")
                )
                database.after_commit(lambda: dispatcher.dispatch(command))
                raise RuntimeError("业务失败")

        assert await load_value(database, item_type, row_id) == "原值"
        assert (await cache.get(keys.TestCacheKeys.ITEM, str(row_id))).value == "原值"
        await cache.delete_all(keys.TestCacheKeys.ITEM)


async def test_cache_failure_after_commit_is_reported_without_pretending_a_rollback(joint_app):
    app, item_type, keys = joint_app
    context = app.state.application_context
    with context.execution():
        database = context.get_bean(SessionProvider)
        cache = context.get_bean(CacheHandler)
        dispatcher = context.get_bean(CacheInvalidationDispatcher)
        client = cache.get_client(keys.TestCacheKeys.ITEM)
        row_id = await insert_row(database, item_type, "提交前")

        # 把 generation 栅栏键写成列表，使提交后的失效在 Redis 侧确定失败。
        generation_key = f"cache_generation:prefix:{keys.TestCacheKeys.ITEM.key}"
        await client.delete(generation_key)
        await client.lpush(generation_key, "broken")
        command = CacheEntryInvalidationCommand(
            cache_key=keys.TestCacheKeys.ITEM, identifier=str(row_id)
        )
        try:
            with pytest.raises(BaseException) as failure:
                async with database.transaction() as session:
                    await session.execute(
                        update(item_type).where(item_type.id == row_id).values(value="已提交")
                    )
                    database.after_commit(
                        lambda: dispatcher.dispatch(command), name="cache-invalidate"
                    )

            # 失败原因必须是缓存操作错误，且明确说明数据已经提交。
            leaves, messages = flatten(failure.value)
            assert any(isinstance(leaf, CacheException) for leaf in leaves)
            assert any("已提交" in message for message in messages)
            # 数据库侧确实已经提交，不能按回滚重试。
            assert await load_value(database, item_type, row_id) == "已提交"
        finally:
            await client.delete(generation_key)
            await cache.delete_all(keys.TestCacheKeys.ITEM)


async def test_optional_after_commit_cache_failure_does_not_break_the_caller(joint_app):
    app, item_type, keys = joint_app
    context = app.state.application_context
    with context.execution():
        database = context.get_bean(SessionProvider)
        cache = context.get_bean(CacheHandler)
        dispatcher = context.get_bean(CacheInvalidationDispatcher)
        client = cache.get_client(keys.TestCacheKeys.ITEM)
        row_id = await insert_row(database, item_type, "初始")
        generation_key = f"cache_generation:prefix:{keys.TestCacheKeys.ITEM.key}"
        await client.delete(generation_key)
        await client.lpush(generation_key, "broken")
        command = CacheEntryInvalidationCommand(
            cache_key=keys.TestCacheKeys.ITEM, identifier=str(row_id)
        )
        try:
            async with database.transaction() as session:
                await session.execute(
                    update(item_type).where(item_type.id == row_id).values(value="写入成功")
                )
                database.after_commit(
                    lambda: dispatcher.dispatch(command), required=False, name="cache-optional"
                )
            await database._transactions.drain_callbacks()

            assert await load_value(database, item_type, row_id) == "写入成功"
            results = {
                result.name: result.success for result in database.get_metrics()["after_commit"]
            }
            assert results["cache-optional"] is False
        finally:
            await client.delete(generation_key)
            await cache.delete_all(keys.TestCacheKeys.ITEM)


async def test_cache_and_database_stay_independent_when_cache_is_unavailable(joint_app):
    app, item_type, keys = joint_app
    context = app.state.application_context
    with context.execution():
        database = context.get_bean(SessionProvider)
        cache = context.get_bean(CacheHandler)
        manager = app.state.cache
        row_id = await insert_row(database, item_type, "可用")
        await manager.close()
        try:
            with pytest.raises(BaseException):
                await cache.get(keys.TestCacheKeys.ITEM, str(row_id))
            # 缓存不可用不会影响数据库读写，两者没有共享事务。
            assert await load_value(database, item_type, row_id) == "可用"
            assert await insert_row(database, item_type, "缓存关闭后仍可写入") > 0
        finally:
            await manager.open()
