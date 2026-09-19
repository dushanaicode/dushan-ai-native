import pytest
from sqlalchemy import select

from framework.starter_data_permission.definitions.constants.data_permission_error_codes import (
    DataPermissionErrorCodes,
)
from framework.starter_data_permission.definitions.enums.data_scope import DataScope
from framework.starter_data_permission.exception.data_permission_exception import (
    DataPermissionException,
)


@pytest.mark.parametrize(
    ("scopes", "custom", "expected"),
    [
        ((DataScope.SELF,), (), [1]),
        ((DataScope.ALL,), (), [1, 2, 3, 4]),
        ((DataScope.DEPT_ONLY,), (), [1, 2]),
        ((DataScope.DEPT_AND_CHILD,), (), [1, 2, 3, 4]),
        ((DataScope.DEPT_CUSTOM,), ("d3",), [1, 4]),
        ((DataScope.DEPT_CUSTOM,), (), [1]),
        ((), (), []),
        ((DataScope.DEPT_ONLY, DataScope.DEPT_CUSTOM), ("d3",), [1, 2, 4]),
        ((DataScope.SELF, DataScope.ALL), (), [1, 2, 3, 4]),
    ],
)
async def test_scopes_execute_in_database(permission_case, scopes, custom, expected):
    case = permission_case
    await case.set_rules(*scopes, custom=custom)
    async with case.enter():
        assert await case.ids() == expected
        assert await case.ids(select(case.Item.__table__.c.id)) == expected
        assert await case.ids(select(case.Item.id).where(case.Item.value > 2)) == [
            i for i in expected if i > 2
        ]
        assert case.provider.calls["rules"] == 1
        assert case.provider.calls["memberships"] <= 1


async def test_no_subject_and_provider_failure(permission_case):
    case = permission_case
    with case.application.execution():
        with pytest.raises(DataPermissionException, match="主体"):
            await case.ids()
    case.provider.failure = RuntimeError("sensitive-provider-input")
    with pytest.raises(DataPermissionException) as error:
        async with case.enter():
            pytest.fail("provider failure must reject entry")
    assert error.value.error_code is DataPermissionErrorCodes.PROVIDER
    assert str(error.value) == "数据权限提供者不可用"
    assert isinstance(error.value.__cause__, RuntimeError)
    assert case.tenant.active == 0
    assert case.service._active == 0


async def test_missing_department_is_configuration_error(permission_case):
    case = permission_case
    await case.set_rules(DataScope.DEPT_ONLY)
    token, _ = case.issue(department=None)
    with pytest.raises(DataPermissionException) as error:
        async with case.enter(token):
            pass
    assert error.value.error_code is DataPermissionErrorCodes.CONFIGURATION


async def test_same_member_id_is_tenant_bound(permission_case):
    case = permission_case
    for tenant, expected in (("t1", [1]), ("t2", [5]), ("t3", [7])):
        await case.set_rules(DataScope.SELF, tenant=tenant)
        token, _ = case.issue(tenant=tenant)
        async with case.enter(token):
            assert await case.ids() == expected
            assert await case.ids(select(case.Item.id).where(case.Item.tenant_id != tenant)) == []
