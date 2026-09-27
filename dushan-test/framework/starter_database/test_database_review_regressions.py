import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy import Column, ForeignKey, Integer, MetaData, Table

from framework.starter_data_permission.core.data_permission_policy import DataPermissionPolicy
from framework.starter_data_permission.core.data_permission_registry import DataPermissionRegistry
from framework.starter_data_permission.definitions.constants.data_permission_error_codes import (
    DataPermissionErrorCodes,
)
from framework.starter_data_permission.exception.data_permission_exception import (
    DataPermissionException,
)
from framework.starter_data_permission.model.data_permission_model import DataPermissionModel
from framework.starter_database.context.database_context import DatabaseContext
from framework.starter_database.definitions.constants.row_access_error_codes import (
    RowAccessErrorCodes,
)
from framework.starter_database.model.model_policy import ModelPolicy
from framework.starter_database.query.row_access_registry import RowAccessRegistry
from framework.starter_database.session.managed_session import ManagedSession
from framework.starter_database.starter.database_starter import DatabaseStarter
from framework.starter_di.context.application_state_enum import ApplicationStateEnum


@pytest.mark.parametrize(
    "action", ["CASCADE", "SET NULL", "SET DEFAULT", None, "NO ACTION", "RESTRICT"]
)
@pytest.mark.parametrize("register_child", [True, False])
def test_row_access_rejects_mutating_on_update_actions(action, register_child):
    metadata = MetaData()
    parent = Table(
        "review_parent",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("code", Integer, unique=True),
    )
    child = Table(
        "review_child",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("parent_code", Integer, ForeignKey(parent.c.code, onupdate=action)),
    )
    entries = {
        table.key: SimpleNamespace(
            table=table, model=None, public=True, tenant_column=None, authority_columns=()
        )
        for table in ((parent, child) if register_child else (parent,))
    }
    failures = []

    def failure(reason):
        failures.append(reason)
        return ValueError("unsupported cascade")

    rule = SimpleNamespace(registry=SimpleNamespace(entries=entries), failure=failure)
    if action in {None, "NO ACTION", "RESTRICT"}:
        assert set(RowAccessRegistry((rule,)).entries) == set(entries)
    else:
        with pytest.raises(ValueError, match="unsupported cascade"):
            RowAccessRegistry((rule,))
        assert failures == [RowAccessErrorCodes.CONFIGURATION]


async def test_unregistered_cascading_child_is_rejected_when_binding_managed_session():
    metadata = MetaData()
    parent = Table(
        "binding_parent",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("code", Integer, unique=True),
    )
    Table(
        "binding_child",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("parent_code", Integer, ForeignKey(parent.c.code, onupdate="CASCADE")),
    )
    registry = DataPermissionRegistry([DataPermissionModel(parent, True, None)])
    policy = ModelPolicy(SimpleNamespace(enabled=False), DatabaseContext())
    policy.session_policies.append(DataPermissionPolicy(registry, Mock()))
    with pytest.raises(DataPermissionException) as caught:
        ManagedSession(database_policy=policy, readonly=False, execution=None)
    assert caught.value.error_code == DataPermissionErrorCodes.CONFIGURATION


def test_unrelated_cascade_in_shared_metadata_does_not_block_registered_table():
    metadata = MetaData()
    registered = Table("registered", metadata, Column("id", Integer, primary_key=True))
    other = Table("other", metadata, Column("id", Integer, primary_key=True))
    Table(
        "unrelated_child",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("parent_id", Integer, ForeignKey(other.c.id, onupdate="CASCADE")),
    )
    config = SimpleNamespace(
        table=registered, model=None, public=True, tenant_column=None, authority_columns=()
    )
    rule = SimpleNamespace(registry=SimpleNamespace(entries={registered.key: config}))
    assert set(RowAccessRegistry((rule,)).entries) == {registered.key}


async def test_unexpected_refresh_failure_is_observed_and_keeps_cause_for_close():
    database = SimpleNamespace(
        bind_task_runner=Mock(),
        is_ready=True,
        settings=SimpleNamespace(dynamic_enabled=True, dynamic_refresh_interval_seconds=0),
        replace_sources=AsyncMock(return_value=1),
        close=AsyncMock(),
    )

    async def run(callback):
        return await callback()

    app = SimpleNamespace(state=ApplicationStateEnum.READY, wait_until_ready=AsyncMock())
    starter = DatabaseStarter(database, SimpleNamespace(run=run), app)
    failure = RuntimeError("private provider error")
    loader = SimpleNamespace(load_sources=AsyncMock(side_effect=[(), failure]))
    await starter.attach_source_loader(loader)
    with pytest.raises(RuntimeError) as caught:
        await asyncio.wait_for(starter._refresh_task, 1)
    assert caught.value is failure
    await asyncio.sleep(0)
    assert starter.last_refresh_error == "RuntimeError"
    with pytest.raises(ExceptionGroup) as closed:
        await starter.close()
    assert closed.value.exceptions == (failure,)
    database.close.assert_awaited_once_with()
