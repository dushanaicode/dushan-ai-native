import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    MetaData,
    String,
    Table,
    exists,
    func,
    literal,
    select,
)
from sqlalchemy.orm import (
    aliased,
    column_property,
    foreign,
    joinedload,
    mapped_column,
    relationship,
    selectinload,
    with_expression,
)

from fixtures.config_factory import ConfigFactory
from framework.starter_data_permission.core.data_permission_policy import DataPermissionPolicy
from framework.starter_data_permission.core.data_permission_registry import DataPermissionRegistry
from framework.starter_data_permission.model.data_permission_model import DataPermissionModel
from framework.starter_database.config.database_settings import DatabaseSettings
from framework.starter_database.definitions.constants.database_error_codes import DatabaseErrorCodes
from framework.starter_database.exception.database_exception import DatabaseException
from framework.starter_database.model.base_do import BaseDO
from framework.starter_database.session.session_provider import SessionProvider
from framework.starter_tenant.core.tenant_model_registry import TenantModelRegistry
from framework.starter_tenant.core.tenant_session_policy import TenantSessionPolicy
from framework.starter_tenant.definitions.enums.tenant_model_kind import TenantModelKind
from framework.starter_tenant.exception.tenant_exception import TenantException
from framework.starter_tenant.model.tenant_model import TenantModel


@pytest.fixture
def soft_delete_enabled():
    return True


@pytest.fixture
async def owner_database(soft_delete_enabled):
    case_metadata = MetaData()
    suffix = uuid4().hex

    Item = type(
        "OwnerItem_" + suffix,
        (BaseDO,),
        {
            "__tablename__": "owner_item_" + suffix,
            "metadata": case_metadata,
            "value": mapped_column(String(64), nullable=False),
            "tenant_id": mapped_column(String(32), nullable=False, default="t1"),
            "membership_id": mapped_column(String(32), nullable=False, default="m1"),
        },
    )
    Child = type(
        "OwnerChild_" + suffix,
        (BaseDO,),
        {
            "__tablename__": "owner_child_" + suffix,
            "metadata": case_metadata,
            "parent_id": mapped_column(Integer, nullable=False),
            "tenant_id": mapped_column(String(32), nullable=False, default="t1"),
            "membership_id": mapped_column(String(32), nullable=False, default="m1"),
        },
    )
    Item.children = relationship(
        Child, primaryjoin=Item.id == foreign(Child.parent_id), viewonly=True
    )

    unmanaged = Table(
        "owner_unmanaged_" + suffix,
        case_metadata,
        Column("id", Integer, primary_key=True),
        Column("deleted", Boolean, nullable=False),
    )
    values = ConfigFactory.values()["config"]["models"]["database"]
    values.update(
        enabled=True,
        health_check_enabled=False,
        slow_query_enabled=False,
        dynamic_enabled=True,
        soft_delete_enabled=soft_delete_enabled,
    )
    values["sources"] = [
        dict(
            name=name,
            url="sqlite+aiosqlite:///:memory:",
            role=role,
            weight=100,
            pool=None,
            tls=None,
        )
        for name, role in (("primary", "primary"), ("reporting", "named"))
    ]
    database = SessionProvider(DatabaseSettings.model_validate(values))
    now = datetime.now(UTC).replace(tzinfo=None)
    audit = dict(creator="", updater="", create_time=now, update_time=now)
    async with database.lifespan():
        for name, entry in database._registry.entries.items():
            async with entry.engine.begin() as connection:
                await connection.run_sync(case_metadata.create_all)
                await connection.execute(
                    Item.__table__.insert(),
                    [
                        dict(
                            audit,
                            id=1,
                            value=name,
                            deleted=False,
                            tenant_id="t1",
                            membership_id="m1",
                        ),
                        dict(
                            audit,
                            id=2,
                            value="deleted",
                            deleted=True,
                            tenant_id="t1",
                            membership_id="m1",
                        ),
                        dict(
                            audit,
                            id=3,
                            value="no-live-child",
                            deleted=False,
                            tenant_id="t1",
                            membership_id="m1",
                        ),
                        dict(
                            audit,
                            id=4,
                            value="other-tenant",
                            deleted=False,
                            tenant_id="t2",
                            membership_id="m1",
                        ),
                        dict(
                            audit,
                            id=5,
                            value="other-member",
                            deleted=False,
                            tenant_id="t1",
                            membership_id="m2",
                        ),
                    ],
                )
                await connection.execute(
                    Child.__table__.insert(),
                    [
                        dict(
                            audit,
                            id=11,
                            parent_id=1,
                            deleted=False,
                            tenant_id="t1",
                            membership_id="m1",
                        ),
                        dict(
                            audit,
                            id=12,
                            parent_id=1,
                            deleted=True,
                            tenant_id="t1",
                            membership_id="m1",
                        ),
                        dict(
                            audit,
                            id=13,
                            parent_id=3,
                            deleted=True,
                            tenant_id="t1",
                            membership_id="m1",
                        ),
                        dict(
                            audit,
                            id=14,
                            parent_id=1,
                            deleted=False,
                            tenant_id="t2",
                            membership_id="m1",
                        ),
                        dict(
                            audit,
                            id=15,
                            parent_id=1,
                            deleted=False,
                            tenant_id="t1",
                            membership_id="m2",
                        ),
                    ],
                )
                await connection.execute(unmanaged.insert(), [{"id": 1, "deleted": True}])
        yield database, Item, Child, unmanaged


@pytest.mark.parametrize(
    "source,expected", [(None, "reporting"), ("primary", "primary"), ("reporting", "reporting")]
)
async def test_requires_new_inherits_actual_outer_source_and_explicit_source_wins(
    owner_database, source, expected
):
    database, Item, _, _ = owner_database
    with database.scope(datasource="primary"):
        async with database.transaction(source="reporting") as outer:
            async with database.transaction(source=source, propagation="requires_new") as inner:
                assert inner is not outer
                assert await inner.scalar(select(Item.value).where(Item.id == 1)) == expected
            assert await outer.scalar(select(Item.value).where(Item.id == 1)) == "reporting"


@pytest.mark.parametrize(
    "scope,source,expected",
    [
        (None, None, "primary"),
        ("reporting", None, "reporting"),
        ("reporting", "primary", "primary"),
    ],
)
async def test_requires_new_without_outer_uses_scope_then_primary(
    owner_database, scope, source, expected
):
    database, Item, _, _ = owner_database
    with database.scope(datasource=scope):
        async with database.transaction(source=source, propagation="requires_new") as session:
            assert await session.scalar(select(Item.value).where(Item.id == 1)) == expected


async def test_inherited_requires_new_commit_survives_outer_rollback(owner_database):
    database, Item, _, _ = owner_database
    with pytest.raises(ValueError, match="outer"):
        async with database.transaction(source="reporting") as outer:
            # 外层尚未执行 SQL，避免 SQLite 单写者限制影响独立事务验证。
            async with database.transaction(propagation="requires_new") as inner:
                assert inner is not outer
                inner.add(Item(id=20, value="inner-commit"))
            outer.add(Item(id=21, value="outer-rollback"))
            await outer.flush()
            raise ValueError("outer")
    async with database.read_session(source="reporting") as session:
        assert (await session.scalars(select(Item.id).where(Item.id >= 20))).all() == [20]
    async with database.read_session(source="primary") as session:
        assert (await session.scalars(select(Item.id).where(Item.id >= 20))).all() == []


@pytest.mark.parametrize("failure", [ValueError, asyncio.CancelledError])
async def test_inherited_requires_new_rollback_or_cancel_keeps_outer_usable(
    owner_database, failure
):
    database, Item, _, _ = owner_database
    async with database.transaction(source="reporting") as outer:
        with pytest.raises(failure):
            async with database.transaction(propagation="requires_new") as inner:
                inner.add(Item(id=20, value="inner-rollback"))
                await inner.flush()
                raise failure()
        outer.add(Item(id=21, value="outer-commit"))
    async with database.read_session(source="reporting") as session:
        assert (await session.scalars(select(Item.id).where(Item.id >= 20))).all() == [21]
    assert all(pool["leases"] == 0 for pool in database.get_metrics()["pools"].values())


@pytest.mark.parametrize(
    "scope,source,expected",
    [
        (None, None, "primary"),
        ("primary", None, "primary"),
        ("reporting", None, "reporting"),
        ("reporting", "primary", "primary"),
        ("primary", "reporting", "reporting"),
    ],
)
@pytest.mark.parametrize("parent_finished", [False, True])
async def test_requires_new_child_uses_own_session_and_scope_source(
    owner_database, scope, source, expected, parent_finished
):
    database, Item, _, _ = owner_database
    release = asyncio.Event()

    async def child():
        await release.wait()
        async with database.transaction(source=source, propagation="requires_new") as inner:
            assert inner is not outer
            with pytest.raises(DatabaseException) as caught:
                await outer.scalar(select(Item.value).where(Item.id == 1))
            assert caught.value.error_code is DatabaseErrorCodes.CONTEXT_MISMATCH
            assert await inner.scalar(select(Item.value).where(Item.id == 1)) == expected
            inner.add(Item(id=20, value="child-commit"))

    with database.scope(datasource=scope):
        async with database.transaction(source="reporting") as outer:
            task = asyncio.create_task(child())
            if not parent_finished:
                release.set()
                await task
                assert await outer.scalar(select(Item.value).where(Item.id == 1)) == "reporting"
        if parent_finished:
            release.set()
            await task
    for name in ("primary", "reporting"):
        async with database.read_session(source=name) as session:
            assert (await session.scalars(select(Item.id).where(Item.id == 20))).all() == (
                [20] if name == expected else []
            )
    assert all(pool["leases"] == 0 for pool in database.get_metrics()["pools"].values())


@pytest.mark.parametrize("source", [None, "primary"])
@pytest.mark.parametrize("with_outer", [False, True])
async def test_requires_new_rejects_expired_execution(owner_database, source, with_outer):
    database, _, _, _ = owner_database
    release = asyncio.Event()

    async def child():
        await release.wait()
        async with database.transaction(source=source, propagation="requires_new"):
            pytest.fail("不应使用失效请求上下文")

    with database.scope(datasource="reporting"):
        if with_outer:
            async with database.transaction(source="reporting"):
                task = asyncio.create_task(child())
        else:
            task = asyncio.create_task(child())
    release.set()
    with pytest.raises(DatabaseException) as caught:
        await task
    assert caught.value.error_code is DatabaseErrorCodes.CONTEXT_MISMATCH
    assert all(pool["leases"] == 0 for pool in database.get_metrics()["pools"].values())


@pytest.mark.parametrize("propagation", ["required", "nested"])
@pytest.mark.parametrize("source", [None, "primary"])
@pytest.mark.parametrize("parent_finished", [False, True])
async def test_required_and_nested_reject_foreign_or_expired_outer_frame(
    owner_database, propagation, source, parent_finished
):
    database, _, _, _ = owner_database
    release = asyncio.Event()

    async def child():
        await release.wait()
        with pytest.raises(DatabaseException) as caught:
            async with database.transaction(source=source, propagation=propagation):
                pytest.fail("复用外层事务必须检查任务归属和有效期")
        assert caught.value.error_code is DatabaseErrorCodes.CONTEXT_MISMATCH

    with database.scope(datasource="primary"):
        async with database.transaction(source="reporting"):
            task = asyncio.create_task(child())
            if not parent_finished:
                release.set()
                await task
        if parent_finished:
            release.set()
            await task


@pytest.mark.parametrize("propagation", ["required", "nested"])
async def test_required_and_nested_keep_session_and_source_contract(owner_database, propagation):
    database, _, _, _ = owner_database
    async with database.transaction(source="reporting") as outer:
        async with database.transaction(propagation=propagation) as inner:
            assert inner is outer
        with database.options(datasource="primary"):
            with pytest.raises(ValueError, match="不能切换数据源"):
                async with database.transaction(propagation=propagation):
                    pytest.fail("已有事务不能隐式切换库")


@pytest.mark.parametrize(
    "include_deleted,soft_delete_enabled", [(False, True), (True, True), (False, False)]
)
async def test_soft_delete_core_orm_alias_subqueries_and_aggregate(
    owner_database, include_deleted, soft_delete_enabled
):
    database, Item, _, unmanaged = owner_database
    table = Item.__table__
    core_alias, orm_alias = table.alias("core_item"), aliased(Item)
    subquery = select(table.c.id).subquery()
    cte = select(table.c.id).cte()
    queries = [
        select(table.c.id),
        select(Item.id),
        select(core_alias.c.id),
        select(orm_alias.id),
        select(subquery.c.id),
        select(cte.c.id),
        select(Item.id).where(Item.id.in_(select(table.c.id))),
        select(table.c.id).where(
            exists(select(core_alias.c.id).where(core_alias.c.id == table.c.id))
        ),
        select(table.c.id)
        .where(table.c.id < 3)
        .union_all(select(table.c.id).where(table.c.id >= 3)),
    ]
    expected = [1, 2, 3, 4, 5] if include_deleted or not soft_delete_enabled else [1, 3, 4, 5]
    with database.options(include_deleted=include_deleted):
        async with database.read_session() as session:
            for query in queries:
                original = str(query)
                assert sorted((await session.scalars(query)).all()) == expected
                assert str(query) == original
            assert [
                row.id for row in (await session.execute(select(table).order_by(table.c.id))).all()
            ] == expected
            assert [
                obj.id for obj in (await session.scalars(select(Item).order_by(Item.id))).all()
            ] == expected
            assert await session.scalar(select(func.count()).select_from(table)) == len(expected)
            assert (await session.scalars(select(unmanaged.c.id))).all() == [1]
    async with database.read_session() as session:
        assert await session.scalar(select(func.count()).select_from(table)) == (
            4 if soft_delete_enabled else 5
        )


@pytest.mark.parametrize("orm", [False, True])
@pytest.mark.parametrize("include_deleted", [False, True])
async def test_soft_delete_left_join_preserves_parent_with_only_deleted_children(
    owner_database, orm, include_deleted
):
    database, Item, Child, _ = owner_database
    if orm:
        parent, child = aliased(Item), aliased(Child)
        parent_id, child_id, fk = parent.id, child.id, child.parent_id
    else:
        parent, child = Item.__table__.alias("parent"), Child.__table__.alias("child")
        parent_id, child_id, fk = parent.c.id, child.c.id, child.c.parent_id
    query = (
        select(parent_id, child_id)
        .select_from(parent)
        .outerjoin(child, parent_id == fk)
        .where(parent_id <= 3)
        .order_by(parent_id, child_id)
    )
    original = str(query)
    with database.options(include_deleted=include_deleted):
        async with database.read_session() as session:
            rows = (await session.execute(query)).all()
    assert rows == (
        [(1, 11), (1, 12), (1, 14), (1, 15), (2, None), (3, 13)]
        if include_deleted
        else [(1, 11), (1, 14), (1, 15), (3, None)]
    )
    assert str(query) == original


@pytest.mark.filterwarnings("error::sqlalchemy.exc.SAWarning")
async def test_soft_delete_mixed_columns_and_correlated_aggregate_do_not_add_from(owner_database):
    database, Item, Child, _ = owner_database
    table, child = Item.__table__, Child.__table__
    async with database.read_session() as session:
        assert (await session.scalars(select(table.c.id).where(Item.id == 1))).all() == [1]
        count = (
            select(func.count())
            .select_from(child)
            .where(child.c.parent_id == Item.id)
            .correlate(Item)
            .scalar_subquery()
        )
        query = select(Item.id, count).where(Item.id <= 3).order_by(Item.id)
        assert (await session.execute(query)).all() == [(1, 3), (3, 0)]
        clone = table.to_metadata(MetaData())
        assert await session.scalar(select(func.count()).select_from(clone)) == 5


@pytest.mark.parametrize("loader", [joinedload, selectinload])
@pytest.mark.parametrize("include_deleted", [False, True])
async def test_soft_delete_relationship_loaders_keep_default_visibility(
    owner_database, loader, include_deleted
):
    database, Item, _, _ = owner_database
    with database.options(include_deleted=include_deleted):
        async with database.read_session() as session:
            result = await session.execute(
                select(Item).options(loader(Item.children)).where(Item.id <= 3).order_by(Item.id)
            )
            items = result.unique().scalars().all()
            children = {item.id: sorted(child.id for child in item.children) for item in items}
            assert children == (
                {1: [11, 12, 14, 15], 2: [], 3: [13]}
                if include_deleted
                else {1: [11, 14, 15], 3: []}
            )


@pytest.mark.parametrize("orm", [False, True])
@pytest.mark.parametrize("include_deleted", [False, True])
@pytest.mark.parametrize("use_alias", [False, True])
async def test_soft_delete_recursive_cte_keeps_source_filtering(
    owner_database, orm, include_deleted, use_alias
):
    database, Item, _, _ = owner_database
    if orm:
        model = aliased(Item) if use_alias else Item
        identifier = model.id
    else:
        table = Item.__table__.alias() if use_alias else Item.__table__
        identifier = table.c.id
    tree = select(identifier).where(identifier == 1).cte("item_tree", recursive=True)
    tree = tree.union_all(select(identifier).join(tree, identifier == tree.c.id + 1))
    with database.options(include_deleted=include_deleted):
        async with database.read_session() as session:
            assert (await session.scalars(select(tree.c.id).order_by(tree.c.id))).all() == (
                [1, 2, 3, 4, 5] if include_deleted else [1]
            )


@pytest.fixture
def owner_filtered_database(owner_database):
    database, Item, Child, _ = owner_database
    tenant_context = Mock()
    tenant_context.get_required_tenant_id.return_value = "t1"
    tenant_context.current.return_value = object()
    tenant = TenantSessionPolicy(
        TenantModelRegistry(
            [TenantModel(model, TenantModelKind.TENANT, "tenant_id") for model in (Item, Child)]
        ),
        tenant_context,
    )
    service = Mock()
    service.execution_key.return_value = "owner-execution"
    service.is_exempt.return_value = False
    service.settings.in_clause_chunk_size = 100
    service.current.return_value = SimpleNamespace(
        identity=SimpleNamespace(tenant_id="t1"),
        grant=SimpleNamespace(
            tenant_all=False, membership_ids=frozenset({"m1"}), department_ids=frozenset()
        ),
    )
    permission = DataPermissionPolicy(
        DataPermissionRegistry(
            [
                DataPermissionModel(model, False, "tenant_id", "membership_id")
                for model in (Item, Child)
            ]
        ),
        service,
    )
    with (
        database.use_session_policy(tenant),
        database.use_session_policy(permission),
    ):
        yield owner_database


@pytest.mark.parametrize("include_deleted", [False, True])
async def test_soft_delete_combines_real_tenant_and_permission_policies(
    owner_filtered_database, include_deleted
):
    database, Item, Child, _ = owner_filtered_database
    with database.options(include_deleted=include_deleted):
        async with database.read_session() as session:
            table, child = Item.__table__, Child.__table__.alias("permitted_child")
            for query in (select(Item.id), select(table.c.id)):
                assert sorted((await session.scalars(query)).all()) == (
                    [1, 2, 3] if include_deleted else [1, 3]
                )
            query = (
                select(table.c.id, child.c.id)
                .select_from(table.outerjoin(child, table.c.id == child.c.parent_id))
                .order_by(table.c.id, child.c.id)
            )
            assert (await session.execute(query)).all() == (
                [(1, 11), (1, 12), (2, None), (3, 13)] if include_deleted else [(1, 11), (3, None)]
            )
            tree = select(Item.id).where(Item.id == 1).cte("protected_tree", recursive=True)
            tree = tree.union_all(select(Item.id).join(tree, Item.id == tree.c.id + 1))
            with pytest.raises(TenantException):
                await session.execute(select(tree.c.id))


@pytest.mark.parametrize("core_columns", [False, True])
@pytest.mark.parametrize("use_alias", [False, True])
@pytest.mark.parametrize("include_deleted", [False, True])
async def test_column_property_combines_soft_delete_and_row_permissions(
    owner_filtered_database, core_columns, use_alias, include_deleted
):
    database, Item, Child, _ = owner_filtered_database
    source = Child.__table__.c if core_columns else Child
    Item.child_count = column_property(
        select(func.count(source.id))
        .where(source.parent_id == Item.id)
        .correlate_except(Child)
        .scalar_subquery()
    )
    entity = aliased(Item) if use_alias else Item
    statements = (
        select(entity.id, entity.child_count).order_by(entity.id),
        select(entity.child_count).select_from(entity).order_by(entity.id),
        select(entity).order_by(entity.id),
    )
    original_sql = tuple(str(statement) for statement in statements)
    expected = [(1, 2), (2, 0), (3, 1)] if include_deleted else [(1, 1), (3, 0)]
    with database.options(include_deleted=include_deleted):
        async with database.read_session() as session:
            assert (await session.execute(statements[0])).all() == expected
            assert (await session.scalars(statements[1])).all() == [count for _, count in expected]
            items = (await session.scalars(statements[2])).all()
            assert [(item.id, item.child_count) for item in items] == expected
    assert tuple(str(statement) for statement in statements) == original_sql


@pytest.mark.parametrize("core_columns", [False, True])
@pytest.mark.parametrize("use_alias", [False, True])
@pytest.mark.parametrize("include_deleted", [False, True])
async def test_existing_with_expression_keeps_value_and_combined_filters(
    owner_filtered_database, core_columns, use_alias, include_deleted
):
    database, Item, Child, _ = owner_filtered_database
    source = Child.__table__.c if core_columns else Child
    Item.child_count = column_property(
        select(func.count(source.id))
        .where(source.parent_id == Item.id)
        .correlate_except(Child)
        .scalar_subquery()
    )
    entity = aliased(Item) if use_alias else Item
    expression = (
        select(func.count(source.id) + 10)
        .where(source.parent_id == entity.id)
        .correlate_except(Child)
        .scalar_subquery()
    )
    option = with_expression(entity.child_count, expression)
    statement = select(entity).options(option).order_by(entity.id)
    original_sql = str(statement)
    expected = [(1, 12), (2, 10), (3, 11)] if include_deleted else [(1, 11), (3, 10)]
    with database.options(include_deleted=include_deleted):
        async with database.read_session() as session:
            items = (await session.scalars(statement)).all()
            assert [(item.id, item.child_count) for item in items] == expected
    assert str(statement) == original_sql
    assert statement._with_options == (option,)


@pytest.mark.parametrize("include_deleted", [False, True])
async def test_with_expression_distinguishes_alias_paths(owner_filtered_database, include_deleted):
    database, Item, Child, _ = owner_filtered_database
    Item.child_count = column_property(
        select(func.count(Child.id))
        .where(Child.parent_id == Item.id)
        .correlate_except(Child)
        .scalar_subquery()
    )
    first, second = aliased(Item), aliased(Item)
    options = [
        with_expression(
            entity.child_count,
            select(func.count(Child.id) + offset)
            .where(Child.parent_id == entity.id)
            .correlate_except(Child)
            .scalar_subquery(),
        )
        for entity, offset in ((first, 10), (second, 20))
    ]
    statement = (
        select(first, second).join(second, second.id == 3).where(first.id == 1).options(*options)
    )
    original_sql = str(statement)
    with database.options(include_deleted=include_deleted):
        async with database.read_session() as session:
            left, right = (await session.execute(statement)).one()
            assert (left.id, left.child_count, right.id, right.child_count) == (
                (1, 12, 3, 21) if include_deleted else (1, 11, 3, 20)
            )
    assert str(statement) == original_sql


@pytest.mark.parametrize("include_deleted", [False, True])
async def test_with_expression_keeps_non_query_override(owner_filtered_database, include_deleted):
    database, Item, Child, _ = owner_filtered_database
    Item.child_count = column_property(
        select(func.count(Child.id))
        .where(Child.parent_id == Item.id)
        .correlate_except(Child)
        .scalar_subquery()
    )
    statement = (
        select(Item).options(with_expression(Item.child_count, literal(99))).order_by(Item.id)
    )
    original_sql = str(statement)
    with database.options(include_deleted=include_deleted):
        async with database.read_session() as session:
            items = (await session.scalars(statement)).all()
            assert [(item.id, item.child_count) for item in items] == (
                [(1, 99), (2, 99), (3, 99)] if include_deleted else [(1, 99), (3, 99)]
            )
    assert str(statement) == original_sql
