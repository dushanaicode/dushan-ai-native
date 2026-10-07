import pytest
from fastapi.routing import APIRoute, _iter_routes_with_context
from pydantic import ValidationError

from framework.starter_web.routing.route_policy import RoutePolicy
from module_system.controller.admin.auth.vo.auth.auth_sms_send_req_vo import AuthSmsSendReqVO
from module_system.router import admin_router_main

pytestmark = pytest.mark.unit

ROUTES = {
    (method, context.path if context else route.path): route.endpoint
    for route, context in _iter_routes_with_context(admin_router_main.routes)
    if isinstance(route, APIRoute)
    for method in route.methods
}


def policy(method, path):
    return getattr(ROUTES[(method, "/admin-api/system" + path)], RoutePolicy.ATTRIBUTE)


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/notification/message/my-page"),
        ("GET", "/notification/message/get-my"),
        ("POST", "/auth/send-bind-mobile-code"),
        ("POST", "/auth/bind-mobile"),
    ],
)
def test_personal_routes_require_login_without_management_codes(method, path):
    declared = policy(method, path)
    assert declared.requires_identity and declared.tenant_required
    assert declared.permissions == () and declared.roles == ()


@pytest.mark.parametrize(
    "method,path,permissions",
    [
        ("GET", "/notification/message/get", ("system:notification:message:query",)),
        ("GET", "/sms/channel/callback-url", ("system:sms:channel:update",)),
    ],
)
def test_management_routes_keep_explicit_codes(method, path, permissions):
    assert policy(method, path).permissions == permissions


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/captcha/config"),
        ("POST", "/captcha/get"),
        ("POST", "/captcha/check"),
        ("POST", "/auth/login"),
        ("POST", "/auth/send-sms-code"),
        ("POST", "/auth/send-password-reset-code"),
        ("POST", "/auth/reset-password"),
    ],
)
def test_pre_login_routes_stay_public(method, path):
    assert not policy(method, path).requires_identity


@pytest.mark.parametrize("scene", [21, 22, 23])
def test_anonymous_sms_accepts_login_register_and_recovery(scene):
    assert AuthSmsSendReqVO(mobile="13312341234", scene=scene).scene == scene


@pytest.mark.parametrize("scene", [1, 2, 3, 4, 24])
def test_anonymous_sms_rejects_member_and_bind_scenes(scene):
    with pytest.raises(ValidationError, match="只允许后台登录、注册或找回密码"):
        AuthSmsSendReqVO(mobile="13312341234", scene=scene)
