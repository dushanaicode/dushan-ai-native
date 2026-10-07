from unittest.mock import Mock

import pytest
from fastapi import Request
from fastapi.routing import APIRoute, _iter_routes_with_context

from framework.common.exception import GlobalErrorCodeConstants, ServiceException
from framework.starter_security.integration.security_access import SecurityAccess
from framework.starter_security.public import PermissionSnapshot
from framework.starter_web.public import RoutePolicy
from module_system.controller.admin.auth.auth_controller import AuthController
from module_system.controller.admin.auth.qr_login_controller import QrLoginController
from module_system.controller.admin.captcha.captcha_controller import CaptchaController
from module_system.router import admin_router_main
from module_system.spi.auth.system_request_access_provider import SystemRequestAccessProvider


@pytest.mark.unit
class TestReadonlyRequestAccess:
    @staticmethod
    def _request(method, path="/admin-api/system/user/profile/update", *, headers=()):
        """构造包含实际路径与请求方法的原生请求。"""
        return Request({"type": "http", "method": method, "path": path, "headers": headers})

    @pytest.mark.parametrize("method", ["GET", "HEAD", "OPTIONS"])
    def test_safe_methods_do_not_require_role_check(self, method):
        """所有安全方法均可查看，即使请求路径没有列入认证白名单。"""
        assert not SystemRequestAccessProvider().requires_check(self._request(method))

    @pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE", "CUSTOM"])
    def test_every_other_method_requires_role_check(self, method):
        """写方法和未约定的方法均进入只读角色检查。"""
        assert SystemRequestAccessProvider().requires_check(self._request(method))

    def test_allowlist_matches_only_the_declared_authentication_routes(self):
        """将明确认证端点与实际路由声明核对，防止豁免路径或方法漂移。"""
        endpoints = {
            AuthController.login,
            AuthController.sms_login,
            AuthController.social_login,
            AuthController.social_auth_redirect,
            AuthController.social_callback,
            AuthController.logout,
            AuthController.refresh_token,
            AuthController.send_sms_code,
            AuthController.websocket_ticket,
            QrLoginController.create,
            QrLoginController.poll,
            QrLoginController.scan,
            QrLoginController.confirm,
            QrLoginController.cancel,
            QrLoginController.consume,
            CaptchaController.get_captcha,
            CaptchaController.check_captcha,
        }
        declared = {
            ("POST", context.path if context else route.path)
            for route, context in _iter_routes_with_context(admin_router_main.routes)
            if isinstance(route, APIRoute)
            and route.endpoint in endpoints
            and "POST" in route.methods
        }
        assert len(declared) == 17
        assert SystemRequestAccessProvider.AUTHENTICATION_REQUESTS == declared

    @pytest.mark.parametrize(
        "method,path", sorted(SystemRequestAccessProvider.AUTHENTICATION_REQUESTS)
    )
    def test_authentication_exemption_requires_exact_path_and_method(self, method, path):
        """认证豁免只匹配完整路径与原方法，不放行路径变体或其他写方法。"""
        provider = SystemRequestAccessProvider()
        assert not provider.requires_check(self._request(method, path))
        for other_method in ("PUT", "PATCH", "DELETE", "CUSTOM"):
            assert provider.requires_check(self._request(other_method, path))
        for other_path in ("/prefix" + path, path + "/suffix", path + "/"):
            assert provider.requires_check(self._request(method, other_path))

    @pytest.mark.parametrize("binding", ["demo", "another-account"])
    @pytest.mark.parametrize("roles", [{"readonly"}, {"readonly", "super_admin"}])
    def test_readonly_role_dominates_other_roles_for_every_account(self, binding, roles):
        """只读角色对任意账号生效，超级管理员角色不能抵消它。"""
        snapshot = PermissionSnapshot(
            binding=binding,
            revision="1",
            permissions=frozenset({"*:*:*"}),
            roles=frozenset(roles),
        )
        with pytest.raises(ServiceException) as error:
            SystemRequestAccessProvider().check(self._request("PUT"), snapshot)
        assert error.value.error_code == GlobalErrorCodeConstants.DEMO_DENY
        assert error.value.error_code.code == 901

    @pytest.mark.parametrize("roles", [set(), {"common"}, {"super_admin"}, {"readonly_extra"}])
    def test_account_name_does_not_replace_exact_role_code(self, roles):
        """主体名称即使为 demo，也不能替代精确的 readonly 角色编码。"""
        snapshot = PermissionSnapshot(
            binding="demo", revision="1", permissions=frozenset(), roles=frozenset(roles)
        )
        SystemRequestAccessProvider().check(self._request("PUT"), snapshot)

    @pytest.mark.parametrize(
        "method,path",
        [
            ("POST", "/admin-api/system/oauth2/check-token"),
            ("DELETE", "/admin-api/system/oauth2/token"),
        ],
    )
    async def test_public_basic_authentication_keeps_its_existing_protocol(self, method, path):
        """公开 OAuth2 客户端的 Basic 凭证不能被误当作本站登录令牌。"""
        request = self._request(
            method, path, headers=[(b"authorization", b"Basic Y2xpZW50OnNlY3JldA==")]
        )
        service = Mock()
        access = SecurityAccess(service=service, request_access=SystemRequestAccessProvider())
        async with access.guard(request, RoutePolicy.public()) as identity:
            assert identity is None
        service.authorized.assert_not_called()

    async def test_refresh_does_not_validate_the_existing_bearer(self):
        """刷新请求按白名单放行，不要求已失效的访问令牌仍可认证。"""
        request = self._request(
            "POST",
            "/admin-api/system/auth/refresh-token",
            headers=[(b"authorization", b"Bearer expired")],
        )
        service = Mock()
        access = SecurityAccess(service=service, request_access=SystemRequestAccessProvider())
        async with access.guard(request, RoutePolicy.public()) as identity:
            assert identity is None
        service.authorized.assert_not_called()
