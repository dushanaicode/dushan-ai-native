from contextvars import ContextVar
from types import SimpleNamespace

import pytest
from sqlalchemy import Column, Integer, MetaData, String, Table, select, text, update

import framework.starter_data_permission.core.data_permission_service as service_module
from framework.starter_data_permission.core.data_permission_policy import DataPermissionPolicy
from framework.starter_data_permission.core.data_permission_registry import DataPermissionRegistry
from framework.starter_data_permission.core.data_permission_service import DataPermissionService
from framework.starter_data_permission.definitions.constants.data_permission_error_codes import (
    DataPermissionErrorCodes,
)
from framework.starter_data_permission.exception.data_permission_exception import (
    DataPermissionException,
)
from framework.starter_data_permission.model.data_exemption import DataExemption
from framework.starter_data_permission.model.data_permission_model import DataPermissionModel
from framework.starter_database.definitions.constants.database_error_codes import DatabaseErrorCodes
from framework.starter_database.exception.database_exception import DatabaseException
from framework.starter_database.session.managed_session import ManagedSession


@pytest.fixture
def protected():
    table = Table(
        "review_records",
        MetaData(),
        Column("id", Integer, primary_key=True),
        Column("tenant_id", String),
        Column("membership_id", Integer),
    )
    return DataPermissionModel(table, False, "tenant_id", "membership_id")


@pytest.mark.parametrize("value", ["abc", "01", "0", "9223372036854775808"])
@pytest.mark.parametrize("operation", ["select", "update"])
def test_invalid_provider_integer_id_has_provider_error_on_query_and_write(
    protected, value, operation
):
    frame = SimpleNamespace(
        identity=SimpleNamespace(tenant_id="t"),
        grant=SimpleNamespace(
            tenant_all=False, membership_ids=frozenset({value}), department_ids=frozenset()
        ),
    )
    service = SimpleNamespace(
        current=lambda: frame,
        is_exempt=lambda *args: False,
        settings=SimpleNamespace(in_clause_chunk_size=10),
    )
    policy = DataPermissionPolicy(DataPermissionRegistry([protected]), service)
    with pytest.raises(DataPermissionException) as caught:
        if operation == "select":
            policy.condition(protected, operation)
        else:
            policy.validate_row(protected, {"tenant_id": "t", "membership_id": 1}, operation)
    assert caught.value.error_code is DataPermissionErrorCodes.PROVIDER


@pytest.mark.parametrize("kind", ["prefix", "suffix", "hint", "dml_prefix", "raw_text", "column"])
def test_statement_checks_apply_without_tenant_registry(protected, kind):
    table = protected.table
    unknown = Table("unknown", MetaData(), Column("id", Integer, primary_key=True))
    statement = {
        "prefix": select(table).prefix_with("SQL_NO_CACHE"),
        "suffix": select(table).suffix_with("FOR UPDATE"),
        "hint": select(table).with_statement_hint("untrusted"),
        "dml_prefix": update(table).prefix_with("IGNORE"),
        "raw_text": select(table).where(text("1=1")),
        "column": update(table).values(membership_id=unknown.c.id),
    }[kind]
    registry = DataPermissionRegistry([protected])
    if kind == "raw_text":
        with pytest.raises(DatabaseException) as caught:
            ManagedSession.validate_statement(statement)
        assert caught.value.error_code is DatabaseErrorCodes.OPERATION_FORBIDDEN
        return
    ManagedSession.validate_statement(statement)
    with pytest.raises(DataPermissionException) as caught:
        registry.validate_statement(statement)
    assert caught.value.error_code in {
        DataPermissionErrorCodes.CONFIGURATION,
        DataPermissionErrorCodes.UNREGISTERED,
    }
    assert registry.validate_statement(select(1)) == set()
    assert registry.validate_statement(select(table)) == {table}


def test_duplicate_registry_has_configuration_error(protected):
    with pytest.raises(DataPermissionException) as caught:
        DataPermissionRegistry([protected, protected])
    assert caught.value.error_code is DataPermissionErrorCodes.CONFIGURATION


def test_exemption_execution_keys_keep_distinct_identity_after_exit(monkeypatch):
    # 模拟地址复用；已保存的会话范围不能因两次豁免拥有相同id而相等。
    monkeypatch.setattr(service_module, "id", lambda item: 1, raising=False)
    frame = object()
    service = DataPermissionService.__new__(DataPermissionService)
    service._frame = ContextVar("review_frame", default=frame)
    service._exemptions = ContextVar("review_exemptions", default=())
    service.current = lambda: frame
    first = DataExemption(frame, "records", "select")
    service._exemptions.set((first,))
    before = service.execution_key()
    first.active = False
    second = DataExemption(frame, "records", "select")
    service._exemptions.set((second,))
    after = service.execution_key()
    assert before != after
    second.active = False
    assert before != after
