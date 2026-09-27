from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from sqlalchemy import Integer, String, create_engine, func, insert, select, text
from sqlalchemy.orm import DeclarativeBase, mapped_column

from fixtures.config_factory import ConfigFactory
from framework.starter_data_permission.core.data_permission_policy import DataPermissionPolicy
from framework.starter_data_permission.core.data_permission_registry import DataPermissionRegistry
from framework.starter_data_permission.definitions.constants.data_permission_error_codes import (
    DataPermissionErrorCodes,
)
from framework.starter_data_permission.exception.data_permission_exception import (
    DataPermissionException,
)
from framework.starter_data_permission.model.data_permission_model import DataPermissionModel
from framework.starter_database.config.database_settings import DatabaseSettings
from framework.starter_database.context.database_context import DatabaseContext
from framework.starter_database.model.model_policy import ModelPolicy
from framework.starter_database.session.managed_session import ManagedSession


@contextmanager
def dp_flush_session():
    class Base(DeclarativeBase):
        pass

    class Record(Base):
        __tablename__ = "review_dp_flush_record"
        id = mapped_column(Integer, primary_key=True)
        tenant_id = mapped_column(String, nullable=False)
        membership_id = mapped_column(String, nullable=False)
        value = mapped_column(Integer, nullable=False)

    engine = create_engine("sqlite:///:memory:")
    try:
        Base.metadata.create_all(engine)
        with engine.begin() as connection:
            connection.execute(
                insert(Record.__table__),
                [
                    {"id": 1, "tenant_id": "t1", "membership_id": "m1", "value": 10},
                    {"id": 2, "tenant_id": "t1", "membership_id": "m2", "value": 999},
                ],
            )
        frame = SimpleNamespace(
            identity=SimpleNamespace(tenant_id="t1"),
            grant=SimpleNamespace(
                tenant_all=False, membership_ids=frozenset({"m1"}), department_ids=frozenset()
            ),
        )
        service = SimpleNamespace(
            current=lambda: frame,
            execution_key=lambda: (frame,),
            is_exempt=lambda *args: False,
            settings=SimpleNamespace(in_clause_chunk_size=10),
        )
        registry = DataPermissionRegistry(
            [DataPermissionModel(Record, False, "tenant_id", "membership_id")]
        )
        policy = DataPermissionPolicy(registry, service)
        settings = DatabaseSettings.model_validate(
            ConfigFactory.values()["config"]["models"]["database"]
        )
        model_policy = ModelPolicy(settings, DatabaseContext())
        model_policy.session_policies.append(policy)
        session = ManagedSession(
            bind=engine, database_policy=model_policy, readonly=False, execution=None
        )
        try:
            assert session.access_policies == (policy,)
            yield session, Record
        finally:
            with session.boundary():
                session.rollback()
                session.close()
    finally:
        engine.dispose()


@pytest.mark.parametrize("operation", ["insert", "update"])
@pytest.mark.parametrize("expression_kind", ["text", "nested_text"])
async def test_dp_only_orm_flush_rejects_text_clause(operation, expression_kind):
    with dp_flush_session() as (session, record):
        assert list(session.scalars(select(record.id))) == [1]
        expression = text("(SELECT value FROM review_dp_flush_record WHERE membership_id = 'm2')")
        if expression_kind == "nested_text":
            expression = func.coalesce(expression, 0)
        if operation == "insert":
            session.add(record(id=3, tenant_id="t1", membership_id="m1", value=expression))
        else:
            item = session.scalars(select(record).where(record.id == 1)).one()
            item.value = expression

        with pytest.raises(DataPermissionException) as caught:
            session.flush()
        assert caught.value.error_code is DataPermissionErrorCodes.CONFIGURATION
        with session.boundary():
            session.rollback()
        assert list(session.execute(select(record.id, record.value))) == [(1, 10)]


@pytest.mark.parametrize("operation", ["insert", "update"])
async def test_dp_only_orm_flush_filters_structured_subquery(operation):
    with dp_flush_session() as (session, record):
        expression = select(func.max(record.value)).scalar_subquery()
        if operation == "insert":
            target_id = 3
            session.add(record(id=target_id, tenant_id="t1", membership_id="m1", value=expression))
        else:
            target_id = 1
            item = session.scalars(select(record).where(record.id == target_id)).one()
            item.value = expression

        session.flush()
        assert session.scalar(select(record.value).where(record.id == target_id)) == 10
