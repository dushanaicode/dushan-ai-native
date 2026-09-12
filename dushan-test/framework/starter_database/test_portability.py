import asyncio
from contextvars import Context
from decimal import Decimal

import pytest
from sqlalchemy import event, update


async def test_unicode_decimal_json_and_binary_roundtrip(database_case):
    database, Item, mapper = database_case
    payload = {"语言": ["中文", "🙂"], "enabled": True, "nullable": None}
    original = Item(
        value="渡山🙂", amount=Decimal("12345.6789"), payload=payload, blob=b"\x00\xffdushan"
    )
    await mapper.insert(original)
    loaded = await mapper.select_by_id(original.id)
    assert loaded.value == original.value
    assert loaded.amount == Decimal("12345.6789")
    assert loaded.payload == payload
    assert loaded.blob == b"\x00\xffdushan"


@pytest.mark.parametrize("cancel_count", [1, 2])
async def test_cancel_during_real_database_lock_wait_rolls_back(database_case, cancel_count):
    database, Item, mapper = database_case
    item = await mapper.insert(Item(value="initial"))
    issued = asyncio.Event()
    engine = database._registry.entries["primary"].engine.sync_engine

    def observe(connection, cursor, statement, parameters, context, executemany):
        if context.execution_options.get("database_lock_waiter"):
            issued.set()

    async def waiter():
        async with database.transaction() as session:
            statement = (
                update(Item)
                .where(Item.id == item.id)
                .values(value="must-rollback")
                .execution_options(database_lock_waiter=True)
            )
            if engine.dialect.driver == "aiosqlite":
                # 显式覆盖取消 RETURNING 的路径，不能依赖 ORM 是否自动添加返回列。
                statement = statement.returning(Item.id)
            await session.execute(statement)

    event.listen(engine, "before_cursor_execute", observe)
    task = None
    try:
        async with database.transaction() as session:
            await session.execute(update(Item).where(Item.id == item.id).values(value="holder"))
            task = asyncio.create_task(waiter(), context=Context())
            await asyncio.wait_for(issued.wait(), 2)
            await asyncio.sleep(0.02)
            for _ in range(cancel_count):
                task.cancel("cancel while driver is waiting on a row lock")
                await asyncio.sleep(0.02)
        with pytest.raises(asyncio.CancelledError, match="cancel while driver") as cancelled:
            await asyncio.wait_for(task, 4)
        assert (await mapper.select_by_id(item.id)).value == "holder"
        assert database.get_metrics()["pools"]["primary"]["leases"] == 0
        # 保留取消异常及其 traceback 时也应释放锁，后续写入不能依赖异常被 GC。
        assert cancelled.value.__traceback__ is not None
        assert await mapper.update_by_condition({"value": "after-cancel"}, Item.id == item.id) == 1
        assert (await mapper.select_by_id(item.id)).value == "after-cancel"
    finally:
        event.remove(engine, "before_cursor_execute", observe)
        if task is not None and not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
