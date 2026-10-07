from typing import Protocol

from fastapi import Request

from framework.starter_security.model.permission_snapshot import PermissionSnapshot


class RequestAccessProvider(Protocol):
    """业务模块在路由权限和请求正文解析前补充账号访问约束。"""

    def requires_check(self, request: Request) -> bool:
        """判断请求是否需要账号访问检查，公开入口据此验证已有令牌。"""
        ...

    def check(self, request: Request, snapshot: PermissionSnapshot) -> None:
        """依据当前权威权限快照检查请求，不允许时抛出业务异常。"""
        ...
