import re
import secrets

from fastapi import APIRouter, Depends, Request, Response

from framework.common.exception import ServiceException
from framework.starter_di.public import DiDependency
from framework.starter_protection.public import RateLimitRule, rate_limit
from framework.starter_security.public import SecurityRealm
from framework.starter_web.public import AccessLogPolicy, ResponseHeaders, Result, RoutePolicy
from module_system.config.qr_login_settings import QrLoginSettings
from module_system.config.system_settings import SystemSettings
from module_system.controller.admin.auth.auth_cookies import AuthCookies
from module_system.controller.admin.auth.vo.auth.auth_login_resp_vo import AuthLoginRespVO
from module_system.controller.admin.auth.vo.qr_login.auth_qr_confirm_req_vo import (
    AuthQrConfirmReqVO,
)
from module_system.controller.admin.auth.vo.qr_login.auth_qr_create_resp_vo import (
    AuthQrCreateRespVO,
)
from module_system.controller.admin.auth.vo.qr_login.auth_qr_scan_resp_vo import AuthQrScanRespVO
from module_system.controller.admin.auth.vo.qr_login.auth_qr_status_resp_vo import (
    AuthQrStatusRespVO,
)
from module_system.controller.admin.auth.vo.qr_login.auth_qr_ticket_req_vo import AuthQrTicketReqVO
from module_system.definitions.constants.error_code_constants import ErrorCodeConstants
from module_system.definitions.constants.public_context_constants import PublicContextConstants
from module_system.service.auth.qr_login_service import QrLoginService

qr_login_controller = APIRouter(prefix="/auth/qr-login", tags=["System - 扫码登录"])


class QrLoginController:
    COOKIE = "system_qr_login_binding"
    COOKIE_PATH = "/admin-api/system/auth/qr-login"

    @staticmethod
    def _binding(request: Request) -> str:
        binding = request.cookies.get(QrLoginController.COOKIE)
        if binding is None or re.fullmatch(r"[A-Za-z0-9_-]{43}", binding) is None:
            raise ServiceException(ErrorCodeConstants.AUTH_QR_BROWSER)
        return binding

    @staticmethod
    @qr_login_controller.get("/enabled")
    @RoutePolicy.public()
    @AccessLogPolicy(enabled=False)
    async def enabled(
        settings: QrLoginSettings = Depends(DiDependency(QrLoginSettings)),
    ) -> Result[bool]:
        return Result.success(settings.enabled)

    @staticmethod
    @qr_login_controller.post("/create")
    @RoutePolicy.public(context=PublicContextConstants.TENANT_SELECTION)
    @AccessLogPolicy(enabled=False)
    @rate_limit(
        "system.auth.qr.create",
        rules=(RateLimitRule(algorithm="fixed", capacity=20, window_ms=60000),),
    )
    async def create(
        request: Request,
        response: Response,
        service: QrLoginService = Depends(DiDependency(QrLoginService)),
        settings: SystemSettings = Depends(DiDependency(SystemSettings)),
        qr_settings: QrLoginSettings = Depends(DiDependency(QrLoginSettings)),
    ) -> Result[AuthQrCreateRespVO]:
        """创建与当前浏览器和来源绑定的扫码登录票据。"""
        origin = AuthCookies.require_origin(request, settings)
        binding = (
            secrets.token_urlsafe(32)
            if QrLoginController.COOKIE not in request.cookies
            else QrLoginController._binding(request)
        )
        value = await service.create(binding, origin)
        response.set_cookie(
            QrLoginController.COOKIE,
            binding,
            max_age=qr_settings.expire_seconds + 60,
            httponly=True,
            secure=settings.refresh_cookie_secure,
            samesite="lax",
            path=QrLoginController.COOKIE_PATH,
        )
        response.headers.update(ResponseHeaders.with_no_store())
        return Result.success(value)

    @staticmethod
    @qr_login_controller.post("/poll")
    @RoutePolicy.public()
    @AccessLogPolicy(enabled=False)
    @rate_limit(
        "system.auth.qr.poll",
        rules=(RateLimitRule(algorithm="fixed", capacity=600, window_ms=60000),),
    )
    async def poll(
        request: Request,
        req: AuthQrTicketReqVO,
        service: QrLoginService = Depends(DiDependency(QrLoginService)),
        settings: SystemSettings = Depends(DiDependency(SystemSettings)),
    ) -> Result[AuthQrStatusRespVO]:
        """查询当前浏览器绑定的扫码登录状态。"""
        origin = AuthCookies.require_origin(request, settings)
        return Result.success(
            await service.poll(req.ticket, QrLoginController._binding(request), origin)
        )

    @staticmethod
    @qr_login_controller.post("/scan")
    @RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT)
    @AccessLogPolicy(enabled=False)
    @rate_limit(
        "system.auth.qr.scan",
        rules=(RateLimitRule(algorithm="fixed", capacity=30, window_ms=60000),),
    )
    async def scan(
        request: Request,
        req: AuthQrTicketReqVO,
        service: QrLoginService = Depends(DiDependency(QrLoginService)),
    ) -> Result[AuthQrScanRespVO]:
        return Result.success(await service.scan(req.ticket))

    @staticmethod
    @qr_login_controller.post("/confirm")
    @RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT)
    @AccessLogPolicy(enabled=False)
    @rate_limit(
        "system.auth.qr.confirm",
        rules=(RateLimitRule(algorithm="fixed", capacity=30, window_ms=60000),),
    )
    async def confirm(
        request: Request,
        req: AuthQrConfirmReqVO,
        service: QrLoginService = Depends(DiDependency(QrLoginService)),
    ) -> Result[bool]:
        await service.confirm(req.ticket, req.approve)
        return Result.success(True)

    @staticmethod
    @qr_login_controller.post("/cancel")
    @RoutePolicy.public()
    @AccessLogPolicy(enabled=False)
    @rate_limit(
        "system.auth.qr.cancel",
        rules=(RateLimitRule(algorithm="fixed", capacity=30, window_ms=60000),),
    )
    async def cancel(
        request: Request,
        req: AuthQrTicketReqVO,
        service: QrLoginService = Depends(DiDependency(QrLoginService)),
        settings: SystemSettings = Depends(DiDependency(SystemSettings)),
    ) -> Result[bool]:
        """取消当前浏览器绑定的扫码登录票据。"""
        origin = AuthCookies.require_origin(request, settings)
        await service.cancel(req.ticket, QrLoginController._binding(request), origin)
        return Result.success(True)

    @staticmethod
    @qr_login_controller.post("/consume")
    @RoutePolicy.public()
    @AccessLogPolicy(enabled=False)
    @rate_limit(
        "system.auth.qr.consume",
        rules=(RateLimitRule(algorithm="fixed", capacity=30, window_ms=60000),),
    )
    async def consume(
        request: Request,
        response: Response,
        req: AuthQrTicketReqVO,
        service: QrLoginService = Depends(DiDependency(QrLoginService)),
        settings: SystemSettings = Depends(DiDependency(SystemSettings)),
    ) -> Result[AuthLoginRespVO]:
        """兑换当前浏览器的扫码登录票据并设置刷新 Cookie。"""
        origin = AuthCookies.require_origin(request, settings)
        value = await service.consume(req.ticket, QrLoginController._binding(request), origin)
        AuthCookies.set_refresh(response, value, settings)
        response.headers.update(ResponseHeaders.with_no_store())
        return Result.success(value)
