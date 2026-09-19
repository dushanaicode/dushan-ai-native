from pydantic import BaseModel, ConfigDict, model_validator

from framework.starter_data_permission.definitions.enums.data_scope import DataScope
from framework.starter_security.model.login_session import IdentityId


class DataScopeRule(BaseModel):
    """一个已生效角色或授权来源的范围；角色有效性由业务 Provider 核验。"""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid", hide_input_in_errors=True)

    scope: DataScope
    department_ids: frozenset[IdentityId] = frozenset()

    @model_validator(mode="after")
    def validate_parameters(self):
        if self.scope is not DataScope.DEPT_CUSTOM and self.department_ids:
            raise ValueError("只有自定义范围可以提供部门集合")
        return self

    def __repr_args__(self):
        return iter(())
