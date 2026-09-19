import asyncio

import pytest

from framework.starter_data_permission.definitions.constants.data_permission_error_codes import (
    DataPermissionErrorCodes,
)
from framework.starter_data_permission.definitions.enums.data_scope import DataScope
from framework.starter_data_permission.exception.data_permission_exception import (
    DataPermissionException,
)

pytestmark = pytest.mark.parametrize("permission_case", [{"cache": True}], indirect=True)


async def test_cache_version_revocation_invalidation_and_binding(permission_case):
    case = permission_case
    token, identity = case.issue()
    for _ in range(2):
        async with case.enter(token):
            assert await case.ids() == [1]
    assert case.provider.calls["rules"] == 1
    await case.set_rules(DataScope.ALL)
    current = identity.model_copy(update={"authorization_revision": "2"})
    case.tokens.sessions[identity.token_digest] = current
    async with case.enter(token):
        assert await case.ids() == [1, 2, 3, 4]
        await case.service.invalidate(current)
        with pytest.raises(DataPermissionException):
            await case.ids()
    await case.set_rules()
    current = case.tokens.sessions[identity.token_digest]
    async with case.enter(token):
        assert await case.ids() == []
    assert case.provider.calls["rules"] == 3
    key = case.service.settings.cache_key()
    identifier = case.service._identifier(current)
    with case.application.execution():
        await case.service.cache.set(
            key,
            identifier,
            {
                "binding": "another-application-tenant-subject",
                "revision": current.authorization_revision,
                "grant": {"tenant_all": True, "membership_ids": [], "department_ids": []},
            },
            30,
        )
    with pytest.raises(DataPermissionException) as error:
        async with case.enter(token):
            pass
    assert error.value.error_code is DataPermissionErrorCodes.PROVIDER
    with case.application.execution():
        await case.service.cache.delete(key, identifier)
        await case.service.cache.delete(key, case.service._identifier(identity))


async def test_cache_failure_never_grants_all(permission_case):
    case = permission_case
    case.service.settings = case.service.settings.model_copy(
        update={"provider_timeout_seconds": 0.05}
    )
    with case.application.execution():
        client = case.service.cache.get_client(case.service.settings.cache_key())
        await client.execute_command("CLIENT", "PAUSE", 150)
    with pytest.raises(DataPermissionException) as error:
        async with case.enter():
            pass
    assert error.value.error_code is DataPermissionErrorCodes.PROVIDER
    assert case.service._active == case.tenant.active == 0
    await asyncio.sleep(0.2)
