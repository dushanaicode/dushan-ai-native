import pytest
from sqlalchemy import (
    Column,
    Integer,
    MetaData,
    String,
    Table,
    bindparam,
    column,
    delete,
    func,
    insert,
    literal_column,
    select,
    table,
    text,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import registry

from framework.starter_data_permission.core.data_permission_registry import DataPermissionRegistry
from framework.starter_data_permission.definitions.enums.data_scope import DataScope
from framework.starter_data_permission.exception.data_permission_exception import (
    DataPermissionException,
)
from framework.starter_data_permission.model.data_permission_model import DataPermissionModel
from framework.starter_data_permission.model.data_scope_rule import DataScopeRule
from framework.starter_database.exception.database_exception import DatabaseException

from .test_writes import row


async def test_uncontrolled_table_literal_sql_and_connection_escape(permission_case):
    case = permission_case
    async with case.enter():
        for query in (
            select(table(case.Item.__tablename__, column("id")).c.id),
            select(literal_column("(SELECT MAX(value) FROM " + case.Item.__tablename__ + ")")),
        ):
            with pytest.raises(DataPermissionException):
                await case.ids(query)
        async with case.database.read_session() as session:
            with pytest.raises(DatabaseException):
                await session.execute(text("SELECT 1"))
            with pytest.raises(DatabaseException):
                await session.connection()


async def test_insert_and_flush_scalar_queries_cannot_read_hidden_rows(permission_case):
    case = permission_case
    hidden = (
        select(case.Item.__table__.c.value).where(case.Item.__table__.c.id == 3).scalar_subquery()
    )
    value = func.coalesce(hidden, 0)
    async with case.enter():
        async with case.database.transaction() as session:
            await session.execute(insert(case.Item).values({**row(10), "value": value}))
            session.add(case.Item(**{**row(11), "value": value}))
        async with case.database.read_session() as session:
            assert (await session.get(case.Item, 10)).value == 0
            assert (await session.get(case.Item, 11)).value == 0


async def test_refresh_and_detached_write_validate_database_target(permission_case):
    case = permission_case
    async with AsyncSession(case.schema, expire_on_commit=False) as external:
        hidden = await external.get(case.Item, 3)
        allowed = await external.get(case.Item, 1)
    async with case.enter():
        async with case.database.read_session() as session:
            # read_session 禁止 add；使用写会话验证 refresh/flush，而不是非受管读取。
            assert await session.get(case.Item, 3) is None
        async with case.database.transaction() as session:
            session.add(allowed)
            await session.refresh(allowed)
            assert allowed.value == 1
        with pytest.raises(DatabaseException) as error:
            async with case.database.transaction() as session:
                session.add(hidden)
                await session.refresh(hidden)
        assert error.value.context["category"] == "programming"
        assert "sqlstate" not in error.value.context
        with pytest.raises(DataPermissionException):
            async with case.database.transaction() as session:
                session.add(hidden)
                hidden.value = 123
                await session.flush()


def test_metadata_and_rule_validation():
    metadata = MetaData()
    numeric = Table(
        "invalid",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("tenant_id", Integer),
        Column("membership_id", String),
    )
    with pytest.raises(ValueError):
        DataPermissionModel(numeric, False, "tenant_id", "membership_id")
    with pytest.raises(ValueError):
        DataPermissionModel(numeric, False, None)
    with pytest.raises(ValueError):
        DataPermissionModel(numeric, "false", None)
    with pytest.raises(ValueError):
        DataPermissionModel(numeric, True, None, resource="")
    with pytest.raises(ValueError):
        DataScopeRule(scope=DataScope.SELF, department_ids=frozenset({"d1"}))
    with pytest.raises(ValueError):
        DataScopeRule(scope=98)
    with pytest.raises(DataPermissionException):
        DataPermissionRegistry([type("Unmarked", (), {})])


async def test_execute_parameters_cannot_override_permission_bindings(permission_case):
    case = permission_case
    async with case.enter():
        async with case.database.read_session() as session:
            with pytest.raises(DataPermissionException):
                await session.execute(select(case.Item.id), {"tenant_id_1": "t2"})
            query = select(case.Item.id).where(case.Item.value < bindparam("tenant_id_1"))
            assert (await session.scalars(query, {"tenant_id_1": 100})).all() == [1]


async def test_database_cascade_requires_child_authorization(permission_case):
    case = permission_case
    async with case.enter():
        with pytest.raises(DataPermissionException):
            async with case.database.transaction() as session:
                await session.execute(delete(case.Item).where(case.Item.id == 1))
        assert await case.ids() == [1]
    await case.set_rules(DataScope.ALL)
    async with case.enter():
        async with case.database.transaction() as session:
            await session.execute(delete(case.Item).where(case.Item.id == 1))
        assert 1 not in await case.ids()


async def test_another_mapper_cannot_relabel_a_protected_table(permission_case):
    case = permission_case
    Alternate = type("UndeclaredMapper", (), {})
    mapping = registry()
    mapping.map_imperatively(Alternate, case.Item.__table__)
    try:
        async with case.enter():
            with pytest.raises(DataPermissionException):
                await case.ids(select(Alternate.id))
    finally:
        mapping.dispose()
