from typing import Protocol

from framework.starter_security.model.login_session import LoginSession
from framework.starter_security.model.permission_snapshot import PermissionSnapshot


class PermissionProvider(Protocol):
    """提供指定权威版本的权限；版本已变化时须拒绝，不能返回其他版本冒充。

    权限、角色及相关授权关系变更与 authorization_revision 更新必须原子提交。
    缓存仅存此版本快照，不能缓存 TokenProvider 的账号/会话有效性判断。
    """

    async def snapshot(self, session: LoginSession, *, binding: str) -> PermissionSnapshot: ...
