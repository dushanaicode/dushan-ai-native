import asyncio

import pytest
from sqlalchemy import delete, select, text, update

from framework.common.page.schemas.page_query import PageQuery
from framework.starter_database.exception.after_commit_exception import AfterCommitException
from framework.starter_database.exception.database_exception import DatabaseException
from framework.starter_database.session.session_provider import SessionProvider


async def test_crud_audit_soft_delete_and_portable_limited_purge(database_case):
    database, Item, mapper = database_case
    with database.scope(account_id="alice") as execution:
        items = await mapper.insert_batch([Item(value=str(index)) for index in range(4)])
        assert all(item.creator == "alice" and item.create_time.tzinfo is None for item in items)
        identifiers = [item.id for item in items]
        assert execution.generated_ids == identifiers
        assert await mapper.count() == 4
        assert (await mapper.select_by_id(identifiers[0])).value == "0"
        assert len(await mapper.select_by_ids(identifiers)) == 4
        assert await mapper.delete_by_id(identifiers[0]) == 1
        assert await mapper.select_by_id(identifiers[0]) is None
        assert await mapper.count() == 3
        with database.options(include_deleted=True):
            assert await mapper.count() == 4
            assert (await mapper.select_by_id(identifiers[0])).deleted
        page = await mapper.paginate_query(
            select(Item), PageQuery(page=1, page_size=2), order_by=(Item.id,)
        )
        assert page.total == 3 and len(page.items) == 2
        assert await mapper.purge_limited_by_condition(Item.id > 0, limit=2) == 2
        with database.options(include_deleted=True):
            assert await mapper.count() == 2
    assert database.get_metrics()["pools"]["primary"]["leases"] == 0


async def test_updates_are_explicit_and_never_insert_missing_ids(database_case):
    database, Item, mapper = database_case
    item = await mapper.insert(Item(value="old"))
    with database.scope(account_id="bob"):
        changed = await mapper.update_by_id(Item(id=item.id, value="new"))
        assert changed.value == "new" and changed.updater == "bob"
        assert await mapper.update_by_condition({"value": None}, Item.id == item.id) == 1
    assert (await mapper.select_by_id(item.id)).value is None
    with pytest.raises(LookupError):
        await mapper.update_by_id(Item(id=item.id + 10000, value="missing"))
    with pytest.raises(ValueError):
        await mapper.update_by_condition({"creator": "forged"}, Item.id == item.id)
    with pytest.raises(ValueError):
        await mapper.update_by_condition({"value": "all"})
    assert await mapper.count() == 1


async def test_outer_transaction_rolls_back_multiple_mapper_calls(database_case):
    database, Item, mapper = database_case
    with pytest.raises(RuntimeError, match="business failed"):
        async with database.transaction():
            await mapper.insert(Item(value="first"))
            await mapper.insert(Item(value="second"))
            raise RuntimeError("business failed")
    assert await mapper.count() == 0


async def test_caught_required_failure_marks_outer_rollback_only(database_case):
    database, Item, mapper = database_case
    with pytest.raises(DatabaseException, match="回滚"):
        async with database.transaction():
            await mapper.insert(Item(value="outer"))
            try:
                async with database.transaction():
                    await mapper.insert(Item(value="inner"))
                    raise ValueError("caught")
            except ValueError:
                pass
    assert await mapper.count() == 0


async def test_savepoint_only_rolls_back_inner_and_discards_its_callbacks(database_case):
    database, Item, mapper = database_case
    called = []
    async with database.transaction():
        await mapper.insert(Item(value="outer"))
        try:
            async with database.transaction(propagation="nested"):
                await mapper.insert(Item(value="inner"))
                database.after_commit(lambda: called.append("inner"))
                raise ValueError("savepoint")
        except ValueError:
            pass
        database.after_commit(lambda: called.append("outer"))
    assert [item.value for item in await mapper.select_list()] == ["outer"]
    assert called == ["outer"]


async def test_requires_new_commits_independently(database_case):
    database, Item, mapper = database_case
    with pytest.raises(ValueError):
        async with database.transaction() as outer:
            # 外层还未写入，避免 SQLite 单写者锁阻止独立事务。
            async with database.transaction(propagation="requires_new") as inner:
                assert inner is not outer
                await mapper.insert(Item(value="independent"))
            await mapper.insert(Item(value="rollback"))
            raise ValueError("outer")
    assert [item.value for item in await mapper.select_list()] == ["independent"]


async def test_tasks_do_not_inherit_transaction_session(database_case):
    database, Item, mapper = database_case
    async with database.transaction():
        with pytest.raises(DatabaseException):
            await asyncio.create_task(mapper.count())
    async with database.read_session() as session:
        with pytest.raises(DatabaseException):
            await asyncio.create_task(session.execute(select(Item)))


async def test_delayed_task_cannot_use_expired_transaction(database_case):
    database, Item, mapper = database_case
    release = asyncio.Event()

    async def delayed():
        await release.wait()
        return await mapper.count()

    async with database.transaction():
        task = asyncio.create_task(delayed())
    release.set()
    with pytest.raises(DatabaseException):
        await task


async def test_cancellation_rolls_back_and_releases_pool(database_case):
    database, Item, mapper = database_case
    written = asyncio.Event()

    async def work():
        async with database.transaction():
            await mapper.insert(Item(value="cancel"))
            written.set()
            await asyncio.Event().wait()

    task = asyncio.create_task(work())
    await written.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert await mapper.count() == 0
    assert database.get_metrics()["pools"]["primary"]["leases"] == 0


async def test_managed_boundaries_and_streaming(database_case):
    database, Item, mapper = database_case
    await mapper.insert(Item(value="stream"))
    async with database.read_session() as session:
        for statement in (
            text("SELECT 1"),
            update(Item).values(value="bad"),
            select(Item).with_for_update(),
        ):
            with pytest.raises(DatabaseException):
                await session.execute(statement)
        with pytest.raises(DatabaseException):
            await session.connection()
        result = await session.execute(select(Item))
        with pytest.raises(DatabaseException):
            _ = result.raw
        rows = await session.stream(select(Item))
        assert [item.value async for item in rows.scalars()] == ["stream"]
    with pytest.raises(DatabaseException):
        await session.execute(select(Item))
    async with database.transaction() as session:
        with pytest.raises(DatabaseException):
            await session.commit()
        with pytest.raises(ValueError):
            await mapper.write(delete(Item))


async def test_concurrent_operations_have_distinct_sessions(database_case):
    database, Item, mapper = database_case
    sessions = set()

    async def work(index):
        with database.scope(account_id=f"actor-{index}"):
            async with database.transaction() as session:
                sessions.add(id(session))
                await mapper.insert(Item(value=str(index)))

    await asyncio.gather(*(work(index) for index in range(8)))
    assert len(sessions) == 8
    assert await mapper.count() == 8
    assert {item.creator for item in await mapper.select_list()} == {
        f"actor-{index}" for index in range(8)
    }


async def test_same_model_across_apps_does_not_cross_audit_or_session(
    database_case, database_settings
):
    first, Item, mapper = database_case
    second = SessionProvider(database_settings)
    async with second.lifespan():
        with first.scope(account_id="first"), second.scope(account_id="second"):
            async with first.transaction() as a:
                async with second.transaction() as b:
                    assert a is not b
                    b.add(Item(value="second"))
                a.add(Item(value="first"))
    assert {(item.value, item.creator) for item in await mapper.select_list()} == {
        ("first", "first"),
        ("second", "second"),
    }


async def test_required_after_commit_can_start_new_database_work(database_case):
    database, Item, mapper = database_case
    seen = []

    async def callback():
        seen.append(await mapper.count())
        await mapper.insert(Item(value="callback"))

    with database.scope(account_id="request"):
        async with database.transaction():
            await mapper.insert(Item(value="body"))
            database.after_commit(callback)
    assert seen == [1]
    assert await mapper.count() == 2


async def test_required_callback_failure_reports_committed_data_and_runs_all(database_case):
    database, Item, mapper = database_case
    called = []

    def fail():
        raise RuntimeError("after commit failed")

    with pytest.raises(AfterCommitException) as failure:
        async with database.transaction():
            await mapper.insert(Item(value="committed"))
            database.after_commit(fail)
            database.after_commit(lambda: called.append("last"))
    assert failure.value.committed and not failure.value.retryable
    assert await mapper.count() == 1
    assert called == ["last"]
    assert [result.success for result in database.get_metrics()["after_commit"]] == [False, True]
