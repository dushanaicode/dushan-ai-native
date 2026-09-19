from datetime import UTC, datetime

import pytest
from sqlalchemy import exists, insert, literal, select
from sqlalchemy.orm import aliased

from framework.starter_data_permission.definitions.enums.data_scope import DataScope


async def add_peer(case, identifier, member):
    now = datetime.now(UTC).replace(tzinfo=None)
    async with case.schema.begin() as connection:
        await connection.execute(
            insert(case.Item.__table__),
            {
                "id": identifier,
                "tenant_id": "t1",
                "membership_id": member,
                "dept_id": "d1",
                "name": f"peer-{identifier}",
                "value": identifier,
                "create_time": now,
                "update_time": now,
            },
        )


@pytest.mark.parametrize("reference", ["orm", "core"])
@pytest.mark.parametrize("projection", ["exists", "scalar"])
@pytest.mark.parametrize("depth", [1, 2])
async def test_nested_self_join_filters_hidden_and_allowed_sources(
    permission_case, reference, projection, depth
):
    case = permission_case
    await add_peer(case, 8, "m1")
    model = case.Item
    peer = aliased(model) if reference == "orm" else model.__table__.alias("nested_peer")
    columns = peer if reference == "orm" else peer.c
    async with case.enter():
        for identifier, visible in ((2, False), (8, True)):
            inner = (
                select(columns.name)
                .select_from(model)
                .join(peer, (model.dept_id == columns.dept_id) & (model.id != columns.id))
                .where(columns.id == identifier)
                .correlate(None)
            )
            if projection == "exists":
                if depth == 2:
                    inner = select(literal(1)).where(exists(inner))
                query = select(model.id).where(model.id.in_([1, 8]), exists(inner))
                expected = [(1,), (8,)] if visible else []
            else:
                value = inner.limit(1).scalar_subquery()
                if depth == 2:
                    value = select(value).scalar_subquery()
                query = select(model.id, value).where(model.id.in_([1, 8]))
                expected = [(1, "peer-8"), (8, "peer-8")] if visible else [(1, None), (8, None)]
            async with case.database.read_session() as session:
                assert (await session.execute(query.order_by(model.id))).all() == expected


@pytest.mark.parametrize("reference", ["core_orm", "orm_orm"])
@pytest.mark.parametrize("outer", [False, True])
async def test_alias_join_retains_sources_and_outer_join_semantics(
    permission_case, reference, outer
):
    case = permission_case
    await add_peer(case, 8, "m1")
    model = case.Item
    left = model.__table__.c if reference == "core_orm" else aliased(model, name="left_peer")
    right = aliased(model, name="right_peer")
    condition = (left.dept_id == right.dept_id) & (left.id != right.id)
    if outer:
        condition &= right.membership_id == "m2"
    query = (
        select(left.id, right.id).join(right, condition, isouter=outer).order_by(left.id, right.id)
    )
    expected = [(1, None), (8, None)] if outer else [(1, 8), (8, 1)]
    async with case.enter():
        async with case.database.read_session() as session:
            assert (await session.execute(query)).all() == expected


async def test_reused_alias_statement_rebinds_each_execution(permission_case):
    case = permission_case
    await add_peer(case, 8, "m1")
    await add_peer(case, 9, "m2")
    await case.set_rules(DataScope.SELF, member="m2")
    left, right = aliased(case.Item), aliased(case.Item)
    query = (
        select(left.id, right.id)
        .join(right, (left.dept_id == right.dept_id) & (left.id != right.id))
        .order_by(left.id, right.id)
    )
    for member, expected in (
        ("m1", [(1, 8), (8, 1)]),
        ("m2", [(2, 9), (9, 2)]),
        ("m1", [(1, 8), (8, 1)]),
    ):
        token, _ = case.issue(member=member)
        async with case.enter(token):
            async with case.database.read_session() as session:
                assert (await session.execute(query)).all() == expected


@pytest.mark.parametrize("reference", ["core", "orm", "alias"])
async def test_predicate_alias_and_outer_correlation_remain_filtered(permission_case, reference):
    case = permission_case
    await add_peer(case, 8, "m1")
    model = case.Item
    outer = {"core": model.__table__.c, "orm": model, "alias": aliased(model)}[reference]
    peer = aliased(model)
    relation = (outer.dept_id == peer.dept_id) & (outer.id != peer.id)
    async with case.enter():
        async with case.database.read_session() as session:
            assert (
                await session.execute(select(outer.id).where(relation, peer.id == 2))
            ).all() == []
        for identifier, expected in ((2, []), (8, [(1,)])):
            query = (
                select(outer.id)
                .where(exists(select(literal(1)).where(relation, peer.id == identifier)))
                .order_by(outer.id)
            )
            async with case.database.read_session() as session:
                assert (await session.execute(query)).all() == expected
