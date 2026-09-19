import inspect
from collections.abc import Callable

from fastapi import HTTPException, Request, Security

from framework.common.security.request_identity import RequestIdentity
from framework.starter_security.definitions.constants.security_error_codes import SecurityErrorCodes
from framework.starter_security.exception.security_exception import SecurityException
from framework.starter_web.context.request_context import RequestContext
from framework.starter_web.routing.route_policy import RoutePolicy


class RouteSecurity:
    """把宿主授权提供者保留为原生 FastAPI 依赖，使运行与安全文档共用一个声明。"""

    def __init__(self, policy: RoutePolicy, provider: Callable | None) -> None:
        if provider is None:
            raise ValueError("受保护路由缺少授权提供者，不能注册为公开路由")
        self.policy = policy
        self.__signature__ = inspect.Signature(
            [
                inspect.Parameter("request", inspect.Parameter.KEYWORD_ONLY, annotation=Request),
                inspect.Parameter(
                    "identity",
                    inspect.Parameter.KEYWORD_ONLY,
                    default=Security(provider, scopes=list(policy.permissions)),
                    annotation=RequestIdentity | None,
                ),
            ]
        )

    async def __call__(self, request: Request, identity: RequestIdentity | None) -> None:
        if identity is None:
            raise HTTPException(401, headers={"WWW-Authenticate": "Bearer"})
        if not isinstance(identity, RequestIdentity):
            raise TypeError("授权提供者必须返回 RequestIdentity 或 None")
        if self.policy.tenant_required and identity.tenant_id is None:
            raise SecurityException(SecurityErrorCodes.DENIED, detail="该接口要求租户上下文")
        context = RequestContext.current()
        if context.connection.app is not request.app:
            raise RuntimeError("请求身份与应用归属不一致")
        context.identity = identity
