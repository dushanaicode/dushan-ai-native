from datetime import datetime, timezone

from fastapi import Request

from framework.starter_security.public import (
    SecurityErrorCodes,
    SecurityException,
)
from module_system.config.system_settings import SystemSettings


class AuthCookies:
    @staticmethod
    def check_origin(request: Request, settings: SystemSettings) -> str | None:
        """校验已提供的 Origin，并返回校验后的来源。"""
        origin = request.headers.get("origin")
        if origin is not None and origin not in settings.allowed_origins:
            raise SecurityException(SecurityErrorCodes.ORIGIN, detail=origin)
        return origin

    @staticmethod
    def require_origin(request: Request, settings: SystemSettings) -> str:
        """要求 Origin 存在且属于允许来源。"""
        origin = AuthCookies.check_origin(request, settings)
        if origin is None:
            raise SecurityException(SecurityErrorCodes.ORIGIN, detail="缺少 Origin 请求头")
        return origin

    @staticmethod
    def set_refresh(response, value, settings):
        now = int(datetime.now(timezone.utc).timestamp() * 1000)
        response.set_cookie(
            settings.refresh_cookie_name,
            value.refresh_token,
            max_age=max(0, (value.refresh_expires_time - now) // 1000),
            httponly=True,
            secure=settings.refresh_cookie_secure,
            samesite="lax",
            path="/admin-api/system/auth",
        )

    @staticmethod
    def clear_refresh(response, settings):
        response.delete_cookie(
            settings.refresh_cookie_name,
            httponly=True,
            secure=settings.refresh_cookie_secure,
            samesite="lax",
            path="/admin-api/system/auth",
        )
