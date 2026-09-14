import inspect
from copy import copy, deepcopy
from functools import partial

from fastapi import Depends
from fastapi.routing import APIRoute, _IncludedRouter
from starlette.routing import BaseRoute

from framework.starter_web.response.stream_integrity import StreamIntegrity
from framework.starter_web.routing.endpoint_invocation import EndpointInvocation
from framework.starter_web.routing.route_guard import RouteGuard
from framework.starter_web.routing.route_policy import RoutePolicy
from framework.starter_web.routing.route_security import RouteSecurity
from framework.starter_web.routing.route_trace import RouteTrace
from framework.starter_web.routing.web_route import WebRoute


class RouteSnapshot:
    """用当前 FastAPI 计算的最终声明建立独立路由，运行时不再引用来源 router 的集合。"""

    def __init__(
        self,
        access_provider,
        host_routes: tuple[BaseRoute, ...],
        stream_policy,
        policy_validator=None,
    ) -> None:
        self.access_provider = access_provider
        self.host_routes = host_routes
        self.stream_policy = stream_policy
        self.policy_validator = policy_validator

    def build(self, routes, inherited: RoutePolicy | None):
        result = []
        for route in routes:
            if isinstance(route, _IncludedRouter):
                policy = RoutePolicy.resolve(
                    inherited, getattr(route.original_router, RoutePolicy.ATTRIBUTE, None)
                )
                result.extend(self._included(route, policy))
            else:
                result.append(self._copy_route(route, route, inherited))
        return result

    def _included(self, included, inherited):
        result = []
        for candidate in included.effective_candidates():
            if isinstance(candidate, _IncludedRouter):
                policy = RoutePolicy.resolve(
                    inherited, getattr(candidate.original_router, RoutePolicy.ATTRIBUTE, None)
                )
                result.extend(self._included(candidate, policy))
            else:
                original = candidate.original_route
                effective = (
                    candidate if isinstance(original, APIRoute) else candidate.starlette_route
                )
                result.append(self._copy_route(original, effective, inherited))
        return result

    def _copy_route(self, original, effective, inherited):
        if any(original is host_route for host_route in self.host_routes):
            policy = RoutePolicy.public()
        else:
            owner = getattr(original, "endpoint", original)
            policy = RoutePolicy.resolve(inherited, getattr(owner, RoutePolicy.ATTRIBUTE, None))
        if policy is None:
            raise ValueError(f"业务路由尚未声明公开或受保护：{effective.path}")
        if policy.required_capability is not None and self.policy_validator is None:
            raise ValueError("部署能力声明缺少策略校验提供者")
        if self.policy_validator is not None:
            self.policy_validator(policy)
        if not isinstance(original, APIRoute):
            if policy.requires_identity:
                raise ValueError("受保护 router 不接受 Route/Mount/WebSocket，必须由宿主独立授权")
            route = copy(effective)
            route.app = RouteTrace(effective.app, effective.path)
            return route
        route_class = WebRoute if type(original) is APIRoute else type(original)
        if not issubclass(route_class, WebRoute):
            raise TypeError("自定义 APIRoute 必须继承 WebRoute 以保留上传关闭和请求契约")
        # 仅复制声明值；依赖提供者/生命周期对象继续由原所有者持有，不深拷贝服务。
        options = {
            name: getattr(effective, name) for name in inspect.signature(APIRoute).parameters
        }
        for name in (
            "responses",
            "openapi_extra",
            "response_model_include",
            "response_model_exclude",
        ):
            options[name] = deepcopy(options[name])
        for name in ("tags", "dependencies", "methods"):
            options[name] = list(options[name])
        if policy.requires_identity:
            options["dependencies"].insert(0, Depends(RouteSecurity(policy, self.access_provider)))
        options["endpoint"] = EndpointInvocation.wrap(effective.endpoint)
        policy(options["endpoint"])
        extra = options["openapi_extra"] or {}
        declaration = {
            "mode": "protected" if policy.requires_identity else "public",
            "tenant_required": policy.tenant_required,
        }
        if policy.roles:
            declaration["roles"] = list(policy.roles)
        if policy.scopes:
            declaration["scopes"] = list(policy.scopes)
        if policy.realm is not None:
            declaration["realm"] = policy.realm.value
        if policy.domain is not None:
            declaration["domain"] = policy.domain
        if policy.permission_mode != "all":
            declaration["permission_mode"] = policy.permission_mode
        if policy.role_mode != "all":
            declaration["role_mode"] = policy.role_mode
        if policy.scope_mode != "all":
            declaration["scope_mode"] = policy.scope_mode
        if policy.allowed_tenant_access_modes is not None:
            declaration["allowed_tenant_access_modes"] = sorted(
                mode.value for mode in policy.allowed_tenant_access_modes
            )
        for name in (
            "required_capability",
            "required_entitlement",
            "required_support_resource",
            "required_support_action",
        ):
            value = getattr(policy, name)
            if value is not None:
                declaration[name] = value
        if "x-route-access" in extra and extra["x-route-access"] != declaration:
            raise ValueError(f"OpenAPI 与路由访问声明冲突：{effective.path}")
        options["openapi_extra"] = {**extra, "x-route-access": declaration}
        integrity = getattr(effective.endpoint, StreamIntegrity.ATTRIBUTE, None)
        if integrity is not None:
            declared = {
                "protocol": integrity.protocol,
                "completion_marker": integrity.completion_marker,
            }
            if "x-stream-integrity" in extra and extra["x-stream-integrity"] != declared:
                raise ValueError(f"OpenAPI 与流完整性声明冲突：{effective.path}")
            options["openapi_extra"]["x-stream-integrity"] = declared
        guard = (
            partial(self.access_provider.guard, policy=policy)
            if policy.requires_identity and isinstance(self.access_provider, RouteGuard)
            else None
        )
        return route_class(**options, stream_policy=self.stream_policy, access_guard=guard)
