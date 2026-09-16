import asyncio
from datetime import UTC, datetime

import pytest
from sqlalchemy import delete, exists, func, insert, select, text, union_all, update
from sqlalchemy.orm import aliased, column_property

from framework.starter_data_permission.enums.data_scope import DataScope
from framework.starter_data_permission.exception.data_permission_exception import (
    DataPermissionException,
)

from .test_writes import row


async def test_mixed_core_orm_and_nested_queries_preserve_exact_results(permission_case):
    case = permission_case
    Item, Child = case.Item, case.Child
    a, b = Item.__table__, Child.__table__
    queries = (
        (select(a.c.id).where(Item.value > 0), [(1,)]),
        (select(b.c.id).where(Child.id > 0), [(101,), (103,)]),
        (select(func.count(Child.id)), [(2,)]),
        (select(func.count()).select_from(Child), [(2,)]),
        (union_all(select(Child.id), select(Child.id)), [(101,), (101,), (103,), (103,)]),
        (
            select(
                Item.id,
                select(func.count(Child.id)).where(Child.item_id == Item.id).scalar_subquery(),
            ),
            [(1, 1)],
        ),
        (
            select(
                a.c.id,
                select(func.count(Child.id))
                .where(Child.item_id == a.c.id)
                .correlate(a)
                .scalar_subquery(),
            ),
            [(1, 1)],
        ),
        (select(Item.id).where(exists().where(Child.item_id == Item.id, Child.id == 102)), []),
        (select(Item.id).where(exists().where(Child.item_id == Item.id, Child.id == 101)), [(1,)]),
        (select(Item.id).where(Item.id.in_(select(Child.item_id).where(Child.id == 102))), []),
    )
    async with case.enter():
        async with case.database.read_session() as session:
            for query, expected in queries:
                assert (
                    sorted(tuple(result) for result in (await session.execute(query)).all())
                    == expected
                )
        for source in (select(Child).subquery(), select(b).subquery()):
            async with case.database.read_session() as session:
                values = (await session.scalars(select(aliased(Child, source)))).all()
                assert sorted(value.id for value in values) == [101, 103]


@pytest.mark.parametrize("core_columns", [False, True])
async def test_column_property_is_filtered_for_columns_and_entity_loading(
    permission_case, core_columns
):
    case = permission_case
    Item, Child = case.Item, case.Child
    source = Child.__table__.c if core_columns else Child
    Item.child_count = column_property(
        select(func.count(source.id))
        .where(source.item_id == Item.id)
        .correlate_except(Child)
        .scalar_subquery()
    )
    async with case.enter():
        async with case.database.read_session() as session:
            assert (await session.execute(select(Item.id, Item.child_count))).all() == [(1, 1)]
            assert (await session.scalars(select(Item.child_count))).all() == [1]
            item = (await session.scalars(select(Item))).one()
            assert item.child_count == 1


async def test_all_scope_never_exposes_other_tenants_in_mixed_query(permission_case):
    case = permission_case
    await case.set_rules(DataScope.ALL)
    async with case.enter():
        async with case.database.read_session() as session:
            result = await session.execute(
                select(case.Item.__table__.c.id, case.Item.__table__.c.tenant_id).where(
                    case.Item.value > 0
                )
            )
            assert sorted(result.all()) == [(1, "t1"), (2, "t1"), (3, "t1"), (4, "t1")]


@pytest.mark.parametrize("alias", [False, True])
async def test_update_from_secures_both_hidden_and_allowed_sources(permission_case, alias):
    case = permission_case
    a = case.Item.__table__
    b = case.Child.__table__.alias("source") if alias else case.Child.__table__
    async with case.enter():
        for child_id, expected in ((102, 0), (101, 1)):
            async with case.database.transaction() as session:
                result = await session.execute(
                    update(a)
                    .where(a.c.id == b.c.item_id, a.c.id == 1, b.c.id == child_id)
                    .values(name=b.c.name)
                )
                assert result.rowcount == expected
        async with case.database.read_session() as session:
            assert await session.scalar(select(case.Item.name)) == "child-101"
        async with case.database.transaction() as session:
            result = await session.execute(
                update(case.members)
                .where(case.members.c.id == b.c.item_id, b.c.id == 102)
                .values(member=b.c.name)
            )
            assert result.rowcount == 0


async def test_dml_scalar_queries_filter_reads_in_values_and_where(permission_case):
    case = permission_case
    a, Child = case.Item.__table__, case.Child
    async with case.enter():
        async with case.database.transaction() as session:
            hidden = func.coalesce(
                select(Child.name).where(Child.id == 102).scalar_subquery(), "no-access"
            )
            result = await session.execute(update(a).where(a.c.id == 1).values(name=hidden))
            assert result.rowcount == 1
            await session.execute(insert(case.Item).values({**row(10), "name": hidden + "-insert"}))
            await session.execute(
                update(case.members).where(case.members.c.id == 1).values(member=hidden)
            )
        async with case.database.transaction() as session:
            item = await session.get(case.Item, 1)
            assert item.name == "no-access"
            item.name = func.coalesce(
                select(Child.name).where(Child.id == 102).scalar_subquery(), "no-flush-access"
            )
        for child_id, expected in ((102, 0), (101, 1)):
            async with case.database.transaction() as session:
                result = await session.execute(
                    update(a)
                    .where(a.c.id.in_(select(Child.item_id).where(Child.id == child_id)))
                    .values(value=55)
                )
                assert result.rowcount == expected
        async with case.database.read_session() as session:
            assert (
                await session.scalar(select(case.Item.name).where(case.Item.id == 1))
                == "no-flush-access"
            )
            assert (
                await session.scalar(select(case.Item.name).where(case.Item.id == 10))
                == "no-access-insert"
            )
            assert (
                await session.scalar(select(case.members.c.member).where(case.members.c.id == 1))
                == "no-access"
            )


@pytest.mark.parametrize("cascade", [False, True])
async def test_repeatable_read_checks_current_locked_rows(
    permission_case, permission_target, cascade
):
    if permission_target["name"] != "mysql":
        pytest.skip("验证 InnoDB 默认 REPEATABLE READ")
    case = permission_case
    a, b = case.Item.__table__, case.Child.__table__
    if cascade:
        async with case.schema.begin() as connection:
            await connection.execute(
                update(b).where(b.c.id == 102).values(membership_id="m1", dept_id="d1")
            )
    async with case.enter():
        with pytest.raises(DataPermissionException, match="未授权"):
            async with case.database.transaction() as session:
                assert await session.scalar(select(a.c.value).where(a.c.id == 1)) == 1
                target, identifier = (b, 101) if cascade else (a, 1)
                async with case.schema.begin() as connection:
                    await connection.execute(
                        update(target).where(target.c.id == identifier).values(membership_id="m3")
                    )
                statement = (
                    delete(a).where(a.c.id == 1)
                    if cascade
                    else update(a).where(a.c.id == 1).values(value=77)
                )
                await session.execute(statement)
    async with case.schema.connect() as connection:
        assert (await connection.execute(select(a.c.value).where(a.c.id == 1))).scalar_one() == 1
        assert (await connection.execute(select(b.c.id).where(b.c.id == 101))).scalar_one() == 101


async def test_core_for_update_keeps_real_row_lock(permission_case, permission_target):
    if permission_target["name"] == "sqlite":
        pytest.skip("SQLite 无 SELECT FOR UPDATE")
    from sqlalchemy.exc import DBAPIError

    case = permission_case
    a = case.Item.__table__
    async with case.enter():
        async with case.database.transaction() as session:
            assert (
                await session.scalars(select(a.c.id).where(a.c.id == 1).with_for_update())
            ).all() == [1]
            async with case.schema.connect() as connection:
                with pytest.raises(DBAPIError):
                    await connection.execute(
                        text(f"SELECT id FROM {a.name} WHERE id = 1 FOR UPDATE NOWAIT")
                    )


@pytest.mark.parametrize("permission_case", [{"cache": True}], indirect=True)
async def test_department_is_part_of_cached_scope_identity(permission_case):
    case = permission_case
    await case.set_rules(DataScope.DEPT_ONLY)
    token, identity = case.issue(department="d1")
    moved = identity.model_copy(update={"dept_id": "d2"})
    async with case.enter(token):
        assert await case.ids() == [1, 2]
    case.tokens.sessions[identity.token_digest] = moved
    async with case.enter(token):
        assert await case.ids() == [1, 3]
    with case.application.execution():
        for item in (identity, moved):
            await case.service.cache.delete(
                case.service.settings.cache_key(), case.service._identifier(item)
            )


async def _insert_child(case, identifier, item_id, member, dept="d1"):
    now = datetime.now(UTC).replace(tzinfo=None)
    async with case.schema.begin() as connection:
        await connection.execute(
            insert(case.Child.__table__),
            [
                dict(
                    id=identifier,
                    item_id=item_id,
                    tenant_id="t1",
                    membership_id=member,
                    dept_id=dept,
                    name=f"child-{identifier}",
                    create_time=now,
                    update_time=now,
                )
            ],
        )


async def test_orm_self_join_does_not_leak_unauthorized_sibling(permission_case):
    """自连接：aliased() 别名与未别名引用同现于一条语句时，别名一侧同样必须被过滤。

    row_statement_filter.py 曾经按物理表整体判断"已被 ORM 过滤"，导致未别名一侧
    正确受限时，aliased() 别名一侧完全不受约束，可读到其他成员的任意列。
    """
    case = permission_case
    Child = case.Child
    await _insert_child(case, 104, item_id=1, member="m1")
    Sibling = aliased(Child)
    statement = (
        select(Child.id, Sibling.id, Sibling.membership_id)
        .join(Sibling, Child.item_id == Sibling.item_id)
        .where(Child.id != Sibling.id)
    )
    async with case.enter():
        async with case.database.read_session() as session:
            rows = sorted(tuple(item) for item in (await session.execute(statement)).all())
    assert rows == [(101, 104, "m1"), (104, 101, "m1")]


async def test_core_alias_still_filtered_when_table_also_has_unaliased_orm_reference(
    permission_case,
):
    """同一张表既有未别名 ORM 引用又有 Core .alias() 引用：别名一侧不能被整表跳过。"""
    case = permission_case
    Child = case.Child
    await _insert_child(case, 105, item_id=1, member="m1")
    core_alias = Child.__table__.alias("dp_core_sibling")
    statement = (
        select(Child.id, core_alias.c.id, core_alias.c.membership_id)
        .join(core_alias, Child.item_id == core_alias.c.item_id)
        .where(Child.id != core_alias.c.id)
    )
    async with case.enter():
        async with case.database.read_session() as session:
            rows = sorted(tuple(item) for item in (await session.execute(statement)).all())
    assert rows == [(101, 105, "m1"), (105, 101, "m1")]


async def test_orm_and_core_aliases_combined_with_unaliased_reference(permission_case):
    """三方混用：未别名 ORM 实体 + ORM 别名 + Core 别名，均指向同一张表。"""
    case = permission_case
    Child = case.Child
    await _insert_child(case, 106, item_id=1, member="m1")
    OrmSibling = aliased(Child)
    core_sibling = Child.__table__.alias("dp_triple_core")
    statement = (
        select(Child.id, OrmSibling.id, core_sibling.c.id, core_sibling.c.membership_id)
        .join(OrmSibling, Child.item_id == OrmSibling.item_id)
        .join(core_sibling, Child.item_id == core_sibling.c.item_id)
        .where(Child.item_id == 1)
    )
    async with case.enter():
        async with case.database.read_session() as session:
            rows = (await session.execute(statement)).all()
    authorized = {101, 106}
    assert rows
    assert all(row.membership_id == "m1" for row in rows)
    assert all(row.id in authorized for row in rows)
    assert all(row[1] in authorized for row in rows)
    assert all(row[2] in authorized for row in rows)


async def test_exists_self_join_alias_does_not_leak_existence(permission_case):
    """EXISTS 内部使用别名与外层未别名实体比较：存在性判断不能因隐藏兄弟记录被污染。"""
    case = permission_case
    Child = case.Child
    Sibling = aliased(Child)
    statement = select(case.Item.id).where(
        exists().where(Sibling.item_id == case.Item.id, Sibling.membership_id == "m3")
    )
    async with case.enter():
        async with case.database.read_session() as session:
            ids = sorted((await session.scalars(statement)).all())
    # 102（m3）挂在 item 1 下，但当前成员（m1）不应看到该 EXISTS 命中 item 1。
    assert 1 not in ids


async def test_self_join_outer_join_preserves_unmatched_left_row(permission_case):
    """别名作为 LEFT OUTER JOIN 右侧时，过滤条件不能落进外层 WHERE 删除合法左行。"""
    case = permission_case
    Child = case.Child
    Sibling = aliased(Child)
    statement = (
        select(Child.id, Sibling.id)
        .outerjoin(Sibling, (Child.item_id == Sibling.item_id) & (Sibling.membership_id == "m3"))
        .where(Child.id == 101)
    )
    async with case.enter():
        async with case.database.read_session() as session:
            rows = (await session.execute(statement)).all()
    # 101 本身合法可见；右侧别名条件（m3）不匹配任何授权范围内的行，但不能因此把
    # 左行 101 从结果中删除——正确语义是 (101, None)。
    assert rows == [(101, None)]


async def test_upsert_repeatable_read_race_rejects_membership_changed_conflict_target(
    permission_case, permission_target
):
    """upsert 命中的已有记录被并发事务改为未授权成员时，必须拒绝而不是沿用旧授权。"""
    if permission_target["name"] != "mysql":
        pytest.skip("InnoDB REPEATABLE READ 快照语义")
    case = permission_case
    a = case.Item.__table__
    started = asyncio.Event()
    proceed = asyncio.Event()

    async def upsert_call():
        started.set()
        await proceed.wait()
        return await case.mapper.upsert(
            {
                "tenant_id": "t1",
                "name": "row-1",
                "value": 999,
                "membership_id": "m1",
                "dept_id": "d1",
            },
            conflict_columns=("tenant_id", "name"),
            update_columns=("value",),
        )

    async def concurrent_change():
        await started.wait()
        async with case.schema.begin() as connection:
            await connection.execute(update(a).where(a.c.id == 1).values(membership_id="m3"))
        proceed.set()

    async with case.enter():
        with pytest.raises(DataPermissionException):
            await asyncio.gather(
                asyncio.create_task(upsert_call()), asyncio.create_task(concurrent_change())
            )
    async with case.schema.connect() as connection:
        assert (await connection.execute(select(a.c.value).where(a.c.id == 1))).scalar_one() != 999
