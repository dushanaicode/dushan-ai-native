import re
from contextlib import asynccontextmanager

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, SecurityScopes

from framework.common.security.request_identity import RequestIdentity
from framework.starter_security.definitions.constants.security_error_codes import SecurityErrorCodes
from framework.starter_security.exception.security_exception import SecurityException
from framework.starter_security.model.request_audit import RequestAudit
from framework.starter_web.routing.route_guard import RouteGuard
from framework.starter_web.routing.route_policy import RoutePolicy


class SecurityAccess(RouteGuard):
    """供 create_app(access_provider=SecurityAccess()) 使用的原生 FastAPI 依赖。"""

    VERIFIED = "security_verified_policy"

    @asynccontextmanager
    async def guard(self, request: Request, policy: RoutePolicy):
        service = request.app.state.security
        if service is None:
            raise SecurityException(SecurityErrorCodes.CONFIGURATION)
        token = self._bearer(request)
        async with service.authorized(
            token, policy, request_audit=RequestAudit.from_request(request, token)
        ) as session:
            request.scope["state"][self.VERIFIED] = policy
            try:
                yield RequestIdentity(principal_id=session.account_id, tenant_id=session.tenant_id)
            finally:
                request.scope["state"].pop(self.VERIFIED, None)

    @staticmethod
    def _bearer(request: Request) -> str:
        headers = request.headers.getlist("authorization")
        if not headers:
            raise SecurityException(SecurityErrorCodes.MISSING)
        if (
            len(headers) != 1
            or re.fullmatch(r"Bearer [A-Za-z0-9_-]{32,256}", headers[0], re.IGNORECASE) is None
        ):
            raise SecurityException(SecurityErrorCodes.INVALID)
        return headers[0].split(" ", 1)[1]

    async def __call__(
        self,
        request: Request,
        security_scopes: SecurityScopes,
        credentials: HTTPAuthorizationCredentials | None = Depends(HTTPBearer(auto_error=False)),
    ):
        policy = getattr(request.scope["endpoint"], RoutePolicy.ATTRIBUTE)
        service = request.app.state.security
        if service is None:
            raise SecurityException(SecurityErrorCodes.CONFIGURATION)
        # HTTPBearer 保留原生 OpenAPI/依赖契约；认证只由正文解析前的 guard 执行一次。
        if request.scope["state"].get(self.VERIFIED) is not policy or credentials is None:
            raise SecurityException(SecurityErrorCodes.CONFIGURATION)
        if tuple(security_scopes.scopes) != policy.permissions:
            raise SecurityException(SecurityErrorCodes.CONFIGURATION)
        session = service.context.require()
        return RequestIdentity(principal_id=session.account_id, tenant_id=session.tenant_id)
