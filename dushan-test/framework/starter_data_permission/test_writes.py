import pytest
from sqlalchemy import delete, insert, select, update

from framework.starter_data_permission.exception.data_permission_exception import (
    DataPermissionException,
)
from framework.starter_database.repository.atomic_upsert import AtomicUpsert


def row(identifier=10, *, member="m1", tenant="t1", **extra):
    return dict(
        id=identifier,
        tenant_id=tenant,
        membership_id=member,
        dept_id="d1",
        name=f"row-{identifier}",
        value=10,
        **extra,
    )


async def test_orm_and_core_insert_update_delete(permission_case):
    case = permission_case
    async with case.enter():
        async with case.database.transaction() as session:
            session.add(case.Item(**row()))
        async with case.database.transaction() as session:
            item = await session.get(case.Item, 10)
            item.value = 11
        async with case.database.transaction() as session:
            await session.execute(insert(case.Item), [row(11), row(12)])
            result = await session.execute(
                update(case.Item).where(case.Item.id.in_([10, 11])).values(value=12)
            )
            assert result.rowcount == 2
            result = await session.execute(
                delete(case.Item.__table__).where(case.Item.id.in_([11, 12]))
            )
            assert result.rowcount == 2
        async with case.database.transaction() as session:
            item = await session.get(case.Item, 10)
            assert item.value == 12
            await session.delete(item)
        assert await case.ids() == [1]


@pytest.mark.parametrize(
    "field,value", [("membership_id", "m3"), ("dept_id", "d2"), ("tenant_id", "t2"), ("id", 99)]
)
async def test_ownership_tampering_rejected(permission_case, field, value):
    case = permission_case
    async with case.enter():
        with pytest.raises(DataPermissionException):
            async with case.database.transaction() as session:
                item = await session.get(case.Item, 1)
                setattr(item, field, value)
                await session.flush()
        with pytest.raises(DataPermissionException):
            async with case.database.transaction() as session:
                await session.execute(
                    update(case.Item).where(case.Item.id == 1).values({field: value})
                )
        assert await case.ids() == [1]


@pytest.mark.parametrize("statement_kind", ["update", "delete", "core_insert", "orm_insert"])
async def test_mixed_authorized_batch_fails_atomically(permission_case, statement_kind):
    case = permission_case
    async with case.enter():
        with pytest.raises(DataPermissionException):
            async with case.database.transaction() as session:
                if statement_kind == "update":
                    await session.execute(
                        update(case.Item.__table__).where(case.Item.id.in_([1, 3])).values(value=99)
                    )
                elif statement_kind == "delete":
                    await session.execute(delete(case.Item).where(case.Item.id.in_([1, 5])))
                elif statement_kind == "core_insert":
                    await session.execute(
                        insert(case.Item.__table__), [row(10), row(11, member="m3")]
                    )
                else:
                    session.add_all([case.Item(**row(10)), case.Item(**row(11, tenant="t2"))])
                    await session.flush()
        async with case.database.read_session() as session:
            assert await session.scalar(select(case.Item.value).where(case.Item.id == 1)) == 1
            assert await session.get(case.Item, 10) is None


async def test_upsert_new_allowed_conflict_and_denied_conflict(permission_case):
    case = permission_case
    async with case.enter():
        obj = await case.mapper.upsert(
            row(10), conflict_columns=("tenant_id", "name"), update_columns=("value",)
        )
        assert obj.id == 10
        changed = {**row(10), "value": 20}
        obj = await case.mapper.upsert(
            changed, conflict_columns=("tenant_id", "name"), update_columns=("value",)
        )
        assert obj.value == 20
        for values in (
            {**row(3), "name": "row-3"},
            {**row(20), "name": "row-3"},
            {**row(5), "name": "new-name"},
        ):
            with pytest.raises(DataPermissionException):
                async with case.database.transaction() as session:
                    await session.execute(
                        AtomicUpsert(case.Item.__table__, ("tenant_id", "name"), ("value",)).values(
                            values
                        )
                    )
        assert await case.ids() == [1, 10]


async def test_update_subquery_is_filtered(permission_case):
    case = permission_case
    a = case.Item.__table__
    async with case.enter():
        async with case.database.transaction() as session:
            result = await session.execute(
                update(a).where(a.c.id.in_(select(a.c.id).where(a.c.value < 4))).values(value=30)
            )
            assert result.rowcount == 1
        async with case.database.read_session() as session:
            assert await session.scalar(select(case.Item.value).where(case.Item.id == 1)) == 30
