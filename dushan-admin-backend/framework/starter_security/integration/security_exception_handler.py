from fastapi import Request

from framework.starter_security.exception.security_exception import SecurityException
from framework.starter_web.exception.exception_handler import GlobalExceptionHandler


class SecurityExceptionHandler:
    """复用 Native 业务响应和安全诊断，仅补 Bearer 协议要求的响应头。"""

    def __init__(self, handler: GlobalExceptionHandler):
        self.handler = handler

    async def handle(self, request: Request, error: SecurityException):
        response = await self.handler.handle_business_exception(request, error)
        if error.http_status == 401:
            response.headers["WWW-Authenticate"] = (
                "Bearer" if error.reason == "missing" else 'Bearer error="invalid_token"'
            )
        elif error.http_status == 403:
            response.headers["WWW-Authenticate"] = 'Bearer error="insufficient_scope"'
        return response
