import pytest
from sqlalchemy import insert, select, update

from framework.starter_tenant.exception.tenant_exception import TenantException


async def test_real_assembly_isolates_tenants_and_fills_new_rows(tenant_case):
    case = tenant_case
    Record = case.module.Record
    async with case.enter():
        assert case.tenant.context.get_required_tenant_id() == "1"
        async with case.database.read_session() as session:
            assert (await session.scalars(select(Record.id).order_by(Record.id))).all() == [1, 2]
        async with case.database.transaction() as session:
            await session.execute(
                insert(Record).values(id=10, membership_id="m1", dept_id="d1", name="new", value=10)
            )
        async with case.database.read_session() as session:
            assert (await session.get(Record, 10)).tenant_id == "1"
        with pytest.raises(TenantException, match="归属"):
            async with case.database.transaction() as session:
                await session.execute(
                    insert(Record).values(
                        id=11,
                        tenant_id="2",
                        membership_id="m1",
                        dept_id="d1",
                        name="wrong",
                        value=11,
                    )
                )
    token, _ = case.issue(tenant="2")
    async with case.enter(token):
        async with case.database.read_session() as session:
            assert (await session.scalars(select(Record.id))).all() == [3]
    with case.app.state.application_context.execution():
        with pytest.raises(TenantException, match="上下文"):
            async with case.database.read_session() as session:
                await session.execute(select(Record.id))


@pytest.mark.parametrize("tenant_case", [{"permissions": True}], indirect=True)
async def test_tenant_and_record_permissions_are_composed(tenant_case):
    case = tenant_case
    Record, Child = case.module.Record, case.module.Child
    async with case.enter():
        async with case.database.read_session() as session:
            assert (
                await session.scalars(select(Record.__table__.c.id).where(Record.value > 0))
            ).all() == [1]
            assert (
                await session.scalars(select(Child.__table__.c.id).where(Child.id > 0))
            ).all() == [101]
        async with case.database.transaction() as session:
            result = await session.execute(
                update(Record.__table__)
                .where(Record.id == Child.parent_id, Child.id == 102)
                .values(name=Child.name)
            )
            assert result.rowcount == 0
