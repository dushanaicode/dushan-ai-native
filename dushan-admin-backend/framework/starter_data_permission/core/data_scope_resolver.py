from framework.starter_data_permission.definitions.constants.data_permission_error_codes import (
    DataPermissionErrorCodes,
)
from framework.starter_data_permission.definitions.enums.data_scope import DataScope
from framework.starter_data_permission.exception.data_permission_exception import (
    DataPermissionException,
)
from framework.starter_data_permission.model.data_grant import DataGrant
from framework.starter_data_permission.model.data_scope_rule import DataScopeRule
from framework.starter_data_permission.spi.data_permission_provider import DataPermissionProvider
from framework.starter_security.definitions.enums.tenant_access_mode import TenantAccessMode
from framework.starter_security.model.login_session import LoginSession


class DataScopeResolver:
    """先合并部门再一次展开成员，避免多角色重复读取部门成员。"""

    def __init__(self, provider: DataPermissionProvider):
        self.provider = provider

    async def resolve(self, identity: LoginSession) -> DataGrant:
        if identity.access_mode is not TenantAccessMode.DIRECT_MEMBERSHIP:
            return DataGrant()
        rules = await self.provider.rules(identity)
        if not isinstance(rules, tuple) or any(
            not isinstance(rule, DataScopeRule) or not isinstance(rule.scope, DataScope)
            for rule in rules
        ):
            raise DataPermissionException(DataPermissionErrorCodes.CONFIGURATION)
        if not rules:
            return DataGrant()
        departments = set()
        kinds = {rule.scope for rule in rules}
        for rule in rules:
            self._validate_ids(rule.department_ids)
            if rule.scope is not DataScope.DEPT_CUSTOM and rule.department_ids:
                raise DataPermissionException(DataPermissionErrorCodes.CONFIGURATION)
            departments.update(rule.department_ids)
        if DataScope.ALL in kinds:
            return DataGrant(tenant_all=True)
        if kinds & {DataScope.DEPT_ONLY, DataScope.DEPT_AND_CHILD}:
            if identity.dept_id is None:
                raise DataPermissionException(DataPermissionErrorCodes.CONFIGURATION)
            departments.add(identity.dept_id)
        if DataScope.DEPT_AND_CHILD in kinds:
            descendants = await self.provider.descendants(identity, identity.dept_id)
            self._validate_ids(descendants)
            departments.update(descendants)
        memberships = {identity.membership_id}
        if departments:
            members = await self.provider.memberships(identity, frozenset(departments))
            self._validate_ids(members)
            memberships.update(members)
        return DataGrant(
            membership_ids=frozenset(memberships), department_ids=frozenset(departments)
        )

    @staticmethod
    def _validate_ids(values):
        if not isinstance(values, frozenset) or any(
            not isinstance(value, str) or not value or len(value) > 256 for value in values
        ):
            raise DataPermissionException(DataPermissionErrorCodes.CONFIGURATION)
