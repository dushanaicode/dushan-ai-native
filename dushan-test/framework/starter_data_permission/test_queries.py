import pytest
from sqlalchemy import Column, Integer, MetaData, Table, func, select, union_all
from sqlalchemy.orm import aliased, joinedload, selectinload, subqueryload

from fixtures.config_factory import ConfigFactory
from framework.common.page.config.page_settings import PageSettings
from framework.common.page.schemas.page_query import PageQuery
from framework.starter_data_permission.definitions.constants.data_permission_error_codes import (
    DataPermissionErrorCodes,
)
from framework.starter_data_permission.definitions.enums.data_scope import DataScope
from framework.starter_data_permission.exception.data_permission_exception import (
    DataPermissionException,
)
from framework.starter_database.pagination.sql_paginator import SqlPaginator


async def test_core_alias_subquery_cte_union_and_statistics(permission_case):
    case = permission_case
    await case.set_rules(DataScope.DEPT_ONLY)
    table = case.Item.__table__
    alias = table.alias("owned")
    subquery = select(table.c.id).subquery()
    cte = select(table.c.id).cte("visible")
    entity_alias = aliased(case.Item)
    async with case.enter():
        for statement in (
            select(alias.c.id),
            select(subquery.c.id),
            select(cte.c.id),
            select(entity_alias.id),
            select(case.Item.id).where(case.Item.__table__.c.value < 4),
            select(case.Item.id).where(case.Item.id.in_(select(table.c.id))),
        ):
            assert await case.ids(statement) == [1, 2]
        async with case.database.read_session() as session:
            assert await session.scalar(select(func.count()).select_from(table)) == 2
            assert await session.scalar(select(func.sum(table.c.value))) == 3
            assert (
                await session.scalars(union_all(select(table.c.id), select(table.c.id)))
            ).all() == [1, 2, 1, 2]
            stream = await session.stream_scalars(select(table.c.id).order_by(table.c.id))
            assert [item async for item in stream] == [1, 2]
        assert case.provider.calls["rules"] == 1


@pytest.mark.parametrize("loader", [joinedload, selectinload, subqueryload])
async def test_orm_relationship_loading(permission_case, loader):
    case = permission_case
    async with case.enter():
        async with case.database.read_session() as session:
            values = (
                (await session.scalars(select(case.Item).options(loader(case.Item.children))))
                .unique()
                .all()
            )
            assert [(item.id, [child.id for child in item.children]) for item in values] == [
                (1, [101])
            ]
            assert await session.get(case.Item, 3) is None
            assert await session.get(case.Child, 102) is None


async def test_left_join_preserves_unmatched_parent_and_aggregate(permission_case):
    case = permission_case
    await case.set_rules(DataScope.DEPT_ONLY)
    a, b = case.Item.__table__, case.Child.__table__
    async with case.enter():
        async with case.database.read_session() as session:
            expected = [(1, 101), (2, None)]
            assert (
                await session.execute(
                    select(a.c.id, b.c.id)
                    .select_from(a.outerjoin(b, a.c.id == b.c.item_id))
                    .order_by(a.c.id)
                )
            ).all() == expected
            assert (
                await session.execute(
                    select(case.Item.id, case.Child.id)
                    .outerjoin(case.Child, case.Item.id == case.Child.item_id)
                    .order_by(case.Item.id)
                )
            ).all() == expected
            assert (
                await session.execute(
                    select(a.c.id, func.count(b.c.id))
                    .select_from(a.outerjoin(b, a.c.id == b.c.item_id))
                    .group_by(a.c.id)
                    .order_by(a.c.id)
                )
            ).all() == [(1, 1), (2, 0)]
            # 混用 ORM 实体与 Core JOIN 的右表仍须过滤。
            assert (
                await session.execute(
                    select(case.Item.id, b.c.id).join(b, case.Item.id == b.c.item_id)
                )
            ).all() == [(1, 101)]


async def test_pagination_and_export_share_snapshot(permission_case):
    case = permission_case
    await case.set_rules(DataScope.DEPT_ONLY)
    case.mapper.paginator = SqlPaginator(ConfigFactory.build(PageSettings, "page"))
    async with case.enter():
        async with case.database.read_session() as session:
            page = await case.mapper.paginator.paginate_query(
                session, select(case.Item).order_by(case.Item.id), PageQuery(page=1, page_size=1)
            )
            assert page.total == 2
            assert [item.id for item in page.items] == [1]
        assert await case.ids() == [1, 2]
        assert case.provider.calls["rules"] == 1


async def test_undeclared_and_reconstructed_metadata_rejected(permission_case):
    case = permission_case
    unknown = Table("unregistered", MetaData(), Column("id", Integer, primary_key=True))
    copied = case.Item.__table__.to_metadata(MetaData())
    async with case.enter():
        for table, expected_code in (
            (unknown, DataPermissionErrorCodes.UNREGISTERED),
            (copied, DataPermissionErrorCodes.CONFIGURATION),
        ):
            with pytest.raises(DataPermissionException) as error:
                await case.ids(select(table.c.id))
            assert error.value.error_code is expected_code
