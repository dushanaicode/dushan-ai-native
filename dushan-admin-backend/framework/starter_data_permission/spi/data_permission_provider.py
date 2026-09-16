from typing import Protocol

from framework.starter_data_permission.model.data_scope_rule import DataScopeRule
from framework.starter_security.model.login_session import LoginSession


class DataPermissionProvider(Protocol):
    """业务按当前权威身份读取已生效规则，不信任角色/部门请求参数。

    authorization_revision 必须覆盖规则、部门树和部门成员变化；修改与版本推进
    原子提交，版本不能回退或复用。所有结果限于 session.tenant_id。
    rules 必须先验证角色和规则参数有效；无授权返回空 tuple，故障抛异常。
    revision 在加载结束后核验没有混入新版本。
    四个方法必须使用同一权威主库或具备同等一致性的存储，不能混读滞后副本。
    """

    async def rules(self, session: LoginSession) -> tuple[DataScopeRule, ...]: ...

    async def descendants(self, session: LoginSession, department_id: str) -> frozenset[str]:
        """返回租户内全部递归下级，不只是一层；无下级返回空集合。"""
        ...

    async def memberships(
        self, session: LoginSession, department_ids: frozenset[str]
    ) -> frozenset[str]:
        """先验证全部部门存在且属于当前租户；有效空部门返回空集合，失效部门抛错。"""
        ...

    async def revision(self, session: LoginSession) -> str: ...
