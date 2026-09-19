import asyncio
from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy import MetaData, String, bindparam, insert, update
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import mapped_column

from fixtures.database_fixtures import TARGETS
from framework.starter_database.definitions.constants.database_error_codes import DatabaseErrorCodes
from framework.starter_database.exception.database_exception import DatabaseException
from framework.starter_database.model.base_do import BaseDO
from framework.starter_database.repository.base_mapper import BaseMapper
from framework.starter_database.session.session_provider import SessionProvider


@pytest.fixture(params=["database", "snowflake"])
async def write_case(database_settings, request):
    settings = database_settings.model_copy(
        update={"id_strategy": request.param, "snowflake_machine_id": 23}
    )
    suffix = uuid4().hex[:16]
    Item = type(
        "WriteItem_" + suffix,
        (BaseDO,),
        {
            "__tablename__": "native_write_" + suffix,
            "metadata": MetaData(),
            "name": mapped_column(String(64), unique=True, nullable=False),
            "other": mapped_column(String(64), unique=True, nullable=True),
            "value": mapped_column(String(64), nullable=True),
        },
    )
    database = SessionProvider(settings)
    schema = create_async_engine(settings.sources[0].url.get_secret_value())
    mapper = BaseMapper(Item)
    mapper.session_provider = database
    created = False
    try:
        async with schema.begin() as connection:
            await connection.run_sync(Item.__table__.create)
        created = True
        async with database.lifespan():
            yield database, Item, mapper
    finally:
        try:
            if created:
                async with schema.begin() as connection:
                    await connection.run_sync(Item.__table__.drop)
        finally:
            await schema.dispose()


async def test_core_orm_audit_and_generated_ids_share_policy(write_case):
    database, Item, mapper = write_case
    forged = datetime(2000, 1, 1)
    with database.scope(account_id="actor") as execution:
        async with database.transaction() as session:
            session.add(Item(name="orm", creator="forged", create_time=forged, deleted=True))
            await session.flush()
            await session.execute(
                insert(Item).values(name="model", creator="forged", create_time=forged)
            )
            await session.execute(
                insert(Item.__table__).values(name="table", updater="forged", deleted=True)
            )
            await session.execute(insert(Item), {"name": "params", "update_time": forged})
            await session.execute(
                insert(Item.__table__), [{"name": "params-a"}, {"name": "params-b"}]
            )
            await session.execute(insert(Item).values([{"name": "values-a"}, {"name": "values-b"}]))
            await session.execute(
                insert(Item).values(name=bindparam("business_name")), {"business_name": "bound"}
            )
            await session.execute(insert(Item).values(id=7000001, name="explicit"))
        with database.options(include_deleted=True):
            rows = await mapper.select_list()
        assert {row.name for row in rows} == {
            "orm",
            "model",
            "table",
            "params",
            "params-a",
            "params-b",
            "values-a",
            "values-b",
            "bound",
            "explicit",
        }
        assert all(row.creator == row.updater == "actor" for row in rows)
        assert {row.name for row in rows if row.deleted} == {"orm", "table"}
        assert all(row.create_time > forged and row.update_time == row.create_time for row in rows)
        generated = {row.id for row in rows if row.name != "explicit"}
        assert set(execution.generated_ids) == generated
        assert len(execution.generated_ids) == len(generated)
        assert (await mapper.select_by_id(7000001)).name == "explicit"
        if database.settings.id_strategy == "snowflake":
            assert all(
                abs(
                    (
                        Item.get_create_time_from_id(row.id).replace(tzinfo=None) - row.create_time
                    ).total_seconds()
                )
                < 5
                for row in rows
                if row.name != "explicit"
            )


@pytest.mark.parametrize(
    "database_settings",
    [target for target in TARGETS if target["name"] not in {"mysql", "tidb", "oceanbase"}],
    indirect=True,
    ids=lambda target: target["name"],
)
async def test_core_returning_keeps_requested_columns_and_tracks_identity(write_case):
    database, Item, mapper = write_case
    async with database.transaction() as session:
        with database.scope(account_id="returning") as execution:
            result = await session.execute(
                insert(Item.__table__)
                .values(name="returned")
                .returning(Item.name, Item.create_time)
            )
            assert list(result.keys()) == ["name", "create_time"]
            name, created = result.one()
            assert name == "returned" and isinstance(created, datetime)
            identifiers = list(execution.generated_ids)
    saved = (await mapper.select_list())[0]
    assert identifiers == [saved.id]
    assert saved.create_time == created
    async with database.transaction() as session:
        result = await session.execute(insert(Item).values(name="entity").returning(Item))
        entity = result.scalar_one()
        assert isinstance(entity, Item)
        assert entity.name == "entity" and isinstance(entity.create_time, datetime)
    assert (await mapper.select_by_id(entity.id)).name == "entity"


async def test_core_update_cannot_forge_creation_or_parameter_audit(write_case):
    database, Item, mapper = write_case
    item = await mapper.insert(Item(name="original"))
    with pytest.raises(ValueError):
        await mapper.write(update(Item).where(Item.id == item.id).values(creator="forged"))
    with pytest.raises(ValueError):
        await mapper.write(
            update(Item).where(Item.id == item.id).values(value="bad"), {"updater": "forged"}
        )
    assert (await mapper.select_by_id(item.id)).value is None
    with database.scope(account_id="new-actor"):
        await mapper.write(
            update(Item).where(Item.id == item.id).values(value=bindparam("new_value")),
            {"new_value": "safe"},
        )
    saved = await mapper.select_by_id(item.id)
    assert saved.value == "safe" and saved.updater == "new-actor"


async def test_insert_chunks_return_same_objects_and_rollback_later_failure(write_case):
    database, Item, mapper = write_case
    objects = [Item(name=f"item-{index}") for index in range(3)]
    result = await mapper.insert_batch(objects, chunk_size=1)
    assert result is objects
    with pytest.raises(DatabaseException):
        await mapper.insert_batch([Item(name="first-block"), Item(name="item-0")], chunk_size=1)
    assert {row.name for row in await mapper.select_list()} == {"item-0", "item-1", "item-2"}
    for invalid in (0, -1, True):
        with pytest.raises(ValueError):
            await mapper.insert_batch([], chunk_size=invalid)


async def test_update_chunks_preserve_null_and_rollback_missing_later_id(write_case):
    database, Item, mapper = write_case
    first, second = await mapper.insert_batch(
        [Item(name="first", value="old"), Item(name="second", value="old")]
    )
    with database.scope(account_id="editor"):
        changed = await mapper.update_batch(
            [{"id": second.id, "value": None}, {"id": first.id, "value": "new"}], chunk_size=1
        )
    assert [row.id for row in changed] == [second.id, first.id]
    assert changed[0].value is None and changed[1].value == "new"
    assert all(row.updater == "editor" for row in changed)
    with pytest.raises(LookupError):
        await mapper.update_batch(
            [{"id": first.id, "value": "rollback"}, {"id": -1, "value": "missing"}], chunk_size=1
        )
    assert (await mapper.select_by_id(first.id)).value == "new"
    with pytest.raises(ValueError):
        await mapper.update_batch([{"id": first.id, "creator": "forged"}])
    with pytest.raises(ValueError):
        await mapper.update_batch([{"value": "missing-id"}])
    await mapper.delete_by_id(second.id)
    with pytest.raises(LookupError):
        await mapper.update_batch([{"id": second.id, "value": "revive"}])


async def test_upsert_is_atomic_preserves_creator_and_rejects_deleted(write_case):
    database, Item, mapper = write_case
    with database.scope(account_id="creator"):
        first = await mapper.upsert(
            {"name": "key", "value": "old"}, conflict_columns=["name"], update_columns=["value"]
        )
    with database.scope(account_id="editor") as execution:
        changed = await mapper.upsert(
            {"name": "key", "value": None}, conflict_columns=["name"], update_columns=["value"]
        )
        assert execution.generated_ids == []
    assert changed.id == first.id and changed.value is None
    assert changed.creator == "creator" and changed.updater == "editor"
    assert changed.create_time == first.create_time
    unchanged_actor = await mapper.upsert(
        {"name": "key", "value": None}, conflict_columns=["name"], update_columns=["value"]
    )
    assert unchanged_actor.creator == "creator" and unchanged_actor.updater == "editor"
    await mapper.delete_by_id(first.id)
    with database.options(include_deleted=True):
        with pytest.raises(ValueError):
            await mapper.upsert(
                {"name": "key", "value": "revive"},
                conflict_columns=["name"],
                update_columns=["value"],
            )
        saved = await mapper.select_by_id(first.id)
        assert saved.deleted and saved.value is None


async def test_upsert_other_unique_conflict_cannot_update_wrong_row(write_case):
    database, Item, mapper = write_case
    original = await mapper.insert(Item(name="original", other="unique", value="unchanged"))
    with pytest.raises((ValueError, DatabaseException)):
        await mapper.upsert(
            {"name": "different", "other": "unique", "value": "wrong"},
            conflict_columns=["name"],
            update_columns=["value"],
        )
    assert await mapper.count() == 1
    assert (await mapper.select_by_id(original.id)).value == "unchanged"


async def test_upsert_concurrent_writers_preserve_unique_record(write_case):
    database, Item, mapper = write_case

    async def writer(index):
        with database.scope(account_id=f"writer-{index}"):
            return await mapper.upsert(
                {"name": "concurrent", "value": str(index)},
                conflict_columns=["name"],
                update_columns=["value"],
            )

    # 原生 MERGE 对同时未命中的竞争允许报告真实唯一冲突，不重试或假装成功。
    results = await asyncio.gather(*(writer(index) for index in range(4)), return_exceptions=True)
    successes = [result for result in results if not isinstance(result, BaseException)]
    assert successes
    assert all(isinstance(result, (Item, DatabaseException)) for result in results)
    for result in results:
        if isinstance(result, DatabaseException):
            assert result.error_code in {
                DatabaseErrorCodes.DEADLOCK,
                DatabaseErrorCodes.SERIALIZATION_FAILURE,
            } or (
                result.error_code == DatabaseErrorCodes.UNIQUE_VIOLATION
                and result.context["dialect"] == "dm"
            )
    saved = (await mapper.select_list())[0]
    assert await mapper.count() == 1
    assert {row.id for row in successes} == {saved.id}
    assert saved.value in {str(index) for index in range(4)}
