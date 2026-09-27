from types import SimpleNamespace

import pytest
from sqlalchemy import Column, Integer, MetaData, String, Table, select, text

from framework.starter_database.definitions.constants.database_error_codes import DatabaseErrorCodes
from framework.starter_database.exception.database_exception import DatabaseException
from framework.starter_database.session.managed_session import ManagedSession
from framework.starter_security.definitions.enums.security_realm import SecurityRealm
from framework.starter_security.model.login_session import LoginSession
from framework.starter_tenant.context.tenant_context import TenantContext
from framework.starter_tenant.core.tenant_model_registry import TenantModelRegistry
from framework.starter_tenant.core.tenant_service import TenantService
from framework.starter_tenant.definitions.constants.tenant_error_codes import TenantErrorCodes
from framework.starter_tenant.definitions.enums.tenant_model_kind import TenantModelKind
from framework.starter_tenant.exception.tenant_exception import TenantException
from framework.starter_tenant.model.tenant_model import TenantModel


def test_raw_statement_fragment_is_not_treated_as_a_safe_expression():
    table = Table(
        "review_tenant",
        MetaData(),
        Column("id", Integer, primary_key=True),
        Column("tenant_id", String, nullable=False),
    )
    registry = TenantModelRegistry([TenantModel(table, TenantModelKind.TENANT, "tenant_id")])
    with pytest.raises(DatabaseException) as caught:
        ManagedSession.validate_statement(select(table).where(text("1=1")))
    assert caught.value.error_code is DatabaseErrorCodes.OPERATION_FORBIDDEN
    assert registry.validate_statement(select(table)) == {table}
    assert registry.validate_statement(select(1)) == set()


async def test_missing_provisioning_provider_is_configuration_error_for_account():
    service = TenantService.__new__(TenantService)
    service.ready, service.directory, service.provisioning = True, object(), None
    service.security = SimpleNamespace(
        current=lambda: LoginSession.model_construct(realm=SecurityRealm.ACCOUNT)
    )
    with pytest.raises(TenantException) as caught:
        await service.provision_authenticated(object())
    assert caught.value.error_code is TenantErrorCodes.CONFIGURATION
    assert "部署未提供租户开通能力" in caught.value.msg


def test_resource_denial_does_not_disclose_physical_table_name():
    context = TenantContext.__new__(TenantContext)
    context.current = lambda: SimpleNamespace(resources=())
    with pytest.raises(TenantException) as caught:
        context.authorize_resource("private_physical_table", "select")
    assert caught.value.error_code is TenantErrorCodes.DENIED
    assert "private_physical_table" not in caught.value.msg
