from typing import override

from fastapi import Request

from framework.common.exception import GlobalErrorCodeConstants, ServiceException
from framework.starter_di.public import service
from framework.starter_security.public import PermissionSnapshot, RequestAccessProvider
from module_system.definitions.enums.permission.role_code_enum import RoleCodeEnum


@service(interface=RequestAccessProvider)
class SystemRequestAccessProvider(RequestAccessProvider):
    """只读角色禁止写请求，仅放行网站认证所必需的明确入口。"""

    AUTHENTICATION_REQUESTS = frozenset(
        {
            ("POST", "/admin-api/system/auth/login"),
            ("POST", "/admin-api/system/auth/sms-login"),
            ("POST", "/admin-api/system/auth/social-login"),
            ("POST", "/admin-api/system/auth/social-auth-redirect"),
            ("POST", "/admin-api/system/auth/social-callback"),
            ("POST", "/admin-api/system/auth/logout"),
            ("POST", "/admin-api/system/auth/refresh-token"),
            ("POST", "/admin-api/system/auth/send-sms-code"),
            ("POST", "/admin-api/system/auth/websocket-ticket"),
            ("POST", "/admin-api/system/auth/qr-login/create"),
            ("POST", "/admin-api/system/auth/qr-login/poll"),
            ("POST", "/admin-api/system/auth/qr-login/scan"),
            ("POST", "/admin-api/system/auth/qr-login/confirm"),
            ("POST", "/admin-api/system/auth/qr-login/cancel"),
            ("POST", "/admin-api/system/auth/qr-login/consume"),
            ("POST", "/admin-api/system/captcha/get"),
            ("POST", "/admin-api/system/captcha/check"),
        }
    )

    @override
    def requires_check(self, request: Request) -> bool:
        """按安全方法和完整认证路径放行，不扩展到同前缀的其他操作。"""
        return (
            request.method not in {"GET", "HEAD", "OPTIONS"}
            and (request.method, request.url.path) not in self.AUTHENTICATION_REQUESTS
        )

    @override
    def check(self, request: Request, snapshot: PermissionSnapshot) -> None:
        """只认角色编码，其他角色或管理员权限不能抵消只读限制。"""
        if RoleCodeEnum.READONLY.code in snapshot.roles:
            raise ServiceException(GlobalErrorCodeConstants.DEMO_DENY)
