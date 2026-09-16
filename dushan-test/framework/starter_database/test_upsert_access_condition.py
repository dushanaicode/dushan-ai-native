from decimal import Decimal

from framework.starter_database.repository.atomic_upsert import AtomicUpsert


async def test_atomic_upsert_preserves_access_condition_on_each_dialect(database_case):
    database, Item, mapper = database_case
    item = await mapper.insert(Item(value="allowed", amount=Decimal("1")))
    async with database.transaction() as session:
        statement = AtomicUpsert(Item.__table__, ("id",), ("amount",)).values(
            id=item.id, value="new", amount=Decimal("2")
        )
        statement.access_condition = Item.__table__.c.value == "allowed"
        await session.execute(statement)
    assert (await mapper.select_by_id(item.id)).amount == Decimal("2")
    async with database.transaction() as session:
        statement = AtomicUpsert(Item.__table__, ("id",), ("amount",)).values(
            id=item.id, value="new", amount=Decimal("99")
        )
        statement.access_condition = Item.__table__.c.value == "outside-scope"
        await session.execute(statement)
    assert (await mapper.select_by_id(item.id)).amount == Decimal("2")
