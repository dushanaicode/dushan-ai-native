import pytest
from sqlalchemy import delete, exists, func, insert, select, update
from sqlalchemy.orm import aliased

from framework.starter_database.exception.database_exception import DatabaseException
from framework.starter_database.repository.atomic_upsert import AtomicUpsert
from framework.starter_tenant.exception.tenant_exception import TenantException


async def test_core_orm_alias_join_and_subquery_paths(tenant_case):
    case = tenant_case
    Record, Child = case.module.Record, case.module.Child
    table, child = Record.__table__, Child.__table__
    alias = aliased(Record)
    async with case.enter():
        async with case.database.read_session() as session:
            for query in (
                select(table.c.id).where(Record.value > 0),
                select(alias.id),
                select(Record.id).where(Record.id.in_(select(table.c.id))),
            ):
                assert sorted((await session.scalars(query)).all()) == [1, 2]
            assert await session.scalar(select(func.count()).select_from(table)) == 2
            assert (
                await session.scalars(
                    select(Record.id).where(
                        exists().where(Child.parent_id == Record.id, Child.id == 103)
                    )
                )
            ).all() == []
            assert (
                await session.execute(
                    select(table.c.id, child.c.id)
                    .select_from(table.outerjoin(child, table.c.id == child.c.parent_id))
                    .order_by(table.c.id, child.c.id)
                )
            ).all() == [(1, 101), (1, 102), (2, None)]


async def test_batch_upsert_ownership_and_rollback(tenant_case):
    case = tenant_case
    Record = case.module.Record
    table = Record.__table__
    values = dict(membership_id="m1", dept_id="d1", value=10)
    async with case.enter():
        async with case.database.transaction() as session:
            session.add(Record(id=10, name="orm", **values))
            updated = await session.execute(update(Record).where(Record.id == 10).values(value=11))
            assert updated.rowcount == 1
            await session.execute(
                insert(table),
                [dict(id=11, name="batch1", **values), dict(id=12, name="batch2", **values)],
            )
        async with case.database.transaction() as session:
            await session.execute(
                AtomicUpsert(table, ("tenant_id", "name"), ("value",)).values(
                    id=20, tenant_id="1", name="same", **values
                )
            )
        async with case.database.read_session() as session:
            assert (await session.get(Record, 1)).value == 10
            assert (await session.get(Record, 10)).tenant_id == "1"
        with pytest.raises(TenantException):
            async with case.database.transaction() as session:
                await session.execute(
                    AtomicUpsert(table, ("tenant_id", "name"), ("value",)).values(
                        id=3, tenant_id="1", name="cross-pk", **values
                    )
                )
        with pytest.raises(TenantException):
            async with case.database.transaction() as session:
                await session.execute(update(table).where(table.c.id.in_([1, 3])).values(value=77))
        with pytest.raises(TenantException):
            async with case.database.transaction() as session:
                obj = await session.get(Record, 10)
                obj.tenant_id = "2"
                await session.flush()
        with pytest.raises(RuntimeError):
            async with case.database.transaction() as session:
                await session.execute(delete(table).where(table.c.id == 10))
                raise RuntimeError("rollback")
        async with case.database.read_session() as session:
            assert await session.get(Record, 10) is not None


async def test_cross_tenant_foreign_key_is_rejected_by_real_database(tenant_case):
    case = tenant_case
    async with case.enter():
        with pytest.raises(DatabaseException) as failure:
            async with case.database.transaction() as session:
                await session.execute(
                    insert(case.module.Child).values(
                        id=110, parent_id=3, membership_id="m1", dept_id="d1", name="cross"
                    )
                )
    assert failure.value.context["category"] == "foreign_key"


@pytest.mark.parametrize("tenant_case", [{"permissions": True}], indirect=True)
async def test_composed_preflight_does_not_reveal_hidden_read_conditions(tenant_case):
    case = tenant_case
    table, child = case.module.Record.__table__, case.module.Child.__table__
    async with case.enter():
        results = []
        for child_id in (102, 999):
            async with case.database.transaction() as session:
                outcome = await session.execute(
                    update(table)
                    .where(table.c.id == 3, exists().where(child.c.id == child_id))
                    .values(value=99)
                )
                results.append(outcome.rowcount)
        assert results == [0, 0]
