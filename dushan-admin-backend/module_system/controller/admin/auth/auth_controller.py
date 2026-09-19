import secrets

from fastapi import APIRouter, Depends, Query, Request, Response

from framework.starter_di.public import (
    DiDependency,
)
from framework.starter_protection.public import (
    RateLimitRule,
    rate_limit,
)
from framework.starter_security.public import (
    SecurityContext,
    SecurityErrorCodes,
    SecurityException,
    SecurityRealm,
)
from framework.starter_tenant.public import (
    TenantSettings,
)
from framework.starter_web.public import (
    AccessLogPolicy,
    Result,
    RoutePolicy,
)
from module_system.config.system_settings import SystemSettings
from module_system.controller.admin.auth.auth_cookies import AuthCookies
from module_system.controller.admin.auth.vo.auth_bind_mobile_req_vo import AuthBindMobileReqVO
from module_system.controller.admin.auth.vo.auth_login_req_vo import AuthLoginReqVO
from module_system.controller.admin.auth.vo.auth_login_resp_vo import AuthLoginRespVO
from module_system.controller.admin.auth.vo.auth_permission_info_resp_vo import (
    AuthPermissionInfoRespVO,
)
from module_system.controller.admin.auth.vo.auth_register_req_vo import AuthRegisterReqVO
from module_system.controller.admin.auth.vo.auth_reset_password_req_vo import AuthResetPasswordReqVO
from module_system.controller.admin.auth.vo.auth_sms_login_req_vo import AuthSmsLoginReqVO
from module_system.controller.admin.auth.vo.auth_sms_send_req_vo import AuthSmsSendReqVO
from module_system.controller.admin.auth.vo.auth_social_auth_redirect_req_vo import (
    AuthSocialAuthRedirectReqVO,
)
from module_system.controller.admin.auth.vo.auth_social_login_req_vo import AuthSocialLoginReqVO
from module_system.definitions.enums.logger.login_log_type_enum import LoginLogTypeEnum
from module_system.service.auth.auth_admin_auth_service import AuthAdminAuthService
from module_system.service.auth.system_workload_service import SystemWorkloadService
from module_system.service.oauth2.oauth2_token_service import OAuth2TokenService
from module_system.service.social.social_client_service import SocialClientService

auth_controller = APIRouter(prefix="/auth", tags=["System - 认证管理"])


class AuthController:
    @staticmethod
    @auth_controller.post("/login")
    @RoutePolicy.public()
    @AccessLogPolicy(enabled=False)
    @rate_limit(
        "system.auth.login", rules=(RateLimitRule(algorithm="fixed", capacity=5, window_ms=60000),)
    )
    async def login(
        request: Request,
        response: Response,
        req_vo: AuthLoginReqVO,
        auth: AuthAdminAuthService = Depends(DiDependency(AuthAdminAuthService)),
        workloads: SystemWorkloadService = Depends(DiDependency(SystemWorkloadService)),
        settings: SystemSettings = Depends(DiDependency(SystemSettings)),
        tenant: TenantSettings = Depends(DiDependency(TenantSettings)),
    ) -> Result[AuthLoginRespVO]:
        AuthCookies.check_origin(request, settings)
        async with workloads.scope("system.auth", tenant.default_tenant_id):
            value = await auth.login(req_vo)
        AuthCookies.set_refresh(response, value, settings)
        return Result.success(value)

    @staticmethod
    @auth_controller.post("/register")
    @RoutePolicy.public()
    @AccessLogPolicy(enabled=False)
    @rate_limit(
        "system.auth.register",
        rules=(RateLimitRule(algorithm="fixed", capacity=5, window_ms=60000),),
    )
    async def register(
        request: Request,
        response: Response,
        req_vo: AuthRegisterReqVO,
        auth: AuthAdminAuthService = Depends(DiDependency(AuthAdminAuthService)),
        workloads: SystemWorkloadService = Depends(DiDependency(SystemWorkloadService)),
        settings: SystemSettings = Depends(DiDependency(SystemSettings)),
        tenant: TenantSettings = Depends(DiDependency(TenantSettings)),
    ) -> Result[AuthLoginRespVO]:
        AuthCookies.check_origin(request, settings)
        async with workloads.scope("system.auth", tenant.default_tenant_id):
            value = await auth.register(req_vo)
        AuthCookies.set_refresh(response, value, settings)
        return Result.success(value)

    @staticmethod
    @auth_controller.post("/sms-login")
    @RoutePolicy.public()
    @AccessLogPolicy(enabled=False)
    @rate_limit(
        "system.auth.sms_login",
        rules=(RateLimitRule(algorithm="fixed", capacity=5, window_ms=60000),),
    )
    async def sms_login(
        request: Request,
        response: Response,
        req_vo: AuthSmsLoginReqVO,
        auth: AuthAdminAuthService = Depends(DiDependency(AuthAdminAuthService)),
        workloads: SystemWorkloadService = Depends(DiDependency(SystemWorkloadService)),
        settings: SystemSettings = Depends(DiDependency(SystemSettings)),
        tenant: TenantSettings = Depends(DiDependency(TenantSettings)),
    ) -> Result[AuthLoginRespVO]:
        AuthCookies.check_origin(request, settings)
        async with workloads.scope("system.auth", tenant.default_tenant_id):
            value = await auth.sms_login(req_vo)
        AuthCookies.set_refresh(response, value, settings)
        return Result.success(value)

    @staticmethod
    @auth_controller.post("/social-login")
    @RoutePolicy.public()
    @AccessLogPolicy(enabled=False)
    @rate_limit(
        "system.auth.social_login",
        rules=(RateLimitRule(algorithm="fixed", capacity=5, window_ms=60000),),
    )
    async def social_login(
        request: Request,
        response: Response,
        req_vo: AuthSocialLoginReqVO,
        auth: AuthAdminAuthService = Depends(DiDependency(AuthAdminAuthService)),
        workloads: SystemWorkloadService = Depends(DiDependency(SystemWorkloadService)),
        settings: SystemSettings = Depends(DiDependency(SystemSettings)),
        tenant: TenantSettings = Depends(DiDependency(TenantSettings)),
    ) -> Result[AuthLoginRespVO]:
        AuthCookies.check_origin(request, settings)
        async with workloads.scope("system.auth", tenant.default_tenant_id):
            value = await auth.social_login(req_vo)
        AuthCookies.set_refresh(response, value, settings)
        return Result.success(value)

    @staticmethod
    @auth_controller.post("/send-sms-code")
    @RoutePolicy.public()
    @AccessLogPolicy(enabled=False)
    @rate_limit(
        "system.auth.send_sms_code",
        rules=(RateLimitRule(algorithm="fixed", capacity=5, window_ms=60000),),
    )
    async def send_sms_code(
        request: Request,
        response: Response,
        req_vo: AuthSmsSendReqVO,
        auth: AuthAdminAuthService = Depends(DiDependency(AuthAdminAuthService)),
        workloads: SystemWorkloadService = Depends(DiDependency(SystemWorkloadService)),
        settings: SystemSettings = Depends(DiDependency(SystemSettings)),
        tenant: TenantSettings = Depends(DiDependency(TenantSettings)),
    ) -> Result[bool]:
        AuthCookies.check_origin(request, settings)
        async with workloads.scope("system.auth", tenant.default_tenant_id):
            await auth.send_sms_code(req_vo)
        return Result.success(True)

    @staticmethod
    @auth_controller.post("/reset-password")
    @RoutePolicy.public()
    @AccessLogPolicy(enabled=False)
    @rate_limit(
        "system.auth.reset_password",
        rules=(RateLimitRule(algorithm="fixed", capacity=5, window_ms=60000),),
    )
    async def reset_password(
        request: Request,
        response: Response,
        req_vo: AuthResetPasswordReqVO,
        auth: AuthAdminAuthService = Depends(DiDependency(AuthAdminAuthService)),
        workloads: SystemWorkloadService = Depends(DiDependency(SystemWorkloadService)),
        settings: SystemSettings = Depends(DiDependency(SystemSettings)),
        tenant: TenantSettings = Depends(DiDependency(TenantSettings)),
    ) -> Result[bool]:
        AuthCookies.check_origin(request, settings)
        async with workloads.scope("system.auth", tenant.default_tenant_id):
            await auth.reset_password(req_vo)
        return Result.success(True)

    @staticmethod
    @auth_controller.post("/refresh-token")
    @RoutePolicy.public()
    @AccessLogPolicy(enabled=False)
    async def refresh_token(
        request: Request,
        response: Response,
        auth: AuthAdminAuthService = Depends(DiDependency(AuthAdminAuthService)),
        workloads: SystemWorkloadService = Depends(DiDependency(SystemWorkloadService)),
        settings: SystemSettings = Depends(DiDependency(SystemSettings)),
        tenant: TenantSettings = Depends(DiDependency(TenantSettings)),
    ) -> Result[AuthLoginRespVO]:
        AuthCookies.check_origin(request, settings, required=True)
        secret = request.cookies.get(settings.refresh_cookie_name)
        if secret is None:
            raise SecurityException(SecurityErrorCodes.MISSING)
        async with workloads.scope("system.auth", tenant.default_tenant_id):
            value = await auth.refresh_token(secret, settings.default_client_id)
        AuthCookies.set_refresh(response, value, settings)
        return Result.success(value)

    @staticmethod
    @auth_controller.post("/logout")
    @RoutePolicy.public()
    @AccessLogPolicy(enabled=False)
    async def logout(
        request: Request,
        response: Response,
        auth: AuthAdminAuthService = Depends(DiDependency(AuthAdminAuthService)),
        workloads: SystemWorkloadService = Depends(DiDependency(SystemWorkloadService)),
        settings: SystemSettings = Depends(DiDependency(SystemSettings)),
        tenant: TenantSettings = Depends(DiDependency(TenantSettings)),
    ) -> Result[bool]:
        AuthCookies.check_origin(
            request, settings, required=settings.refresh_cookie_name in request.cookies
        )
        scheme, _, secret = request.headers.get("authorization", "").partition(" ")
        if scheme.lower() == "bearer" and secret:
            async with workloads.scope("system.auth", tenant.default_tenant_id):
                await auth.logout(secret, LoginLogTypeEnum.LOGOUT_SELF.code)
        AuthCookies.clear_refresh(response, settings)
        return Result.success(True)

    @staticmethod
    @auth_controller.get("/get-permission-info")
    @RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT)
    async def get_permission_info(
        auth: AuthAdminAuthService = Depends(DiDependency(AuthAdminAuthService)),
        security: SecurityContext = Depends(DiDependency(SecurityContext)),
    ) -> Result[AuthPermissionInfoRespVO]:
        return Result.success(await auth.get_permission_info(int(security.require().account_id)))

    @staticmethod
    @auth_controller.get("/codes")
    @RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT)
    async def get_codes(
        auth: AuthAdminAuthService = Depends(DiDependency(AuthAdminAuthService)),
        security: SecurityContext = Depends(DiDependency(SecurityContext)),
    ) -> Result[list[str]]:
        info = await auth.get_permission_info(int(security.require().account_id))
        return Result.success(info.permissions)

    @staticmethod
    @auth_controller.post("/bind-mobile")
    @RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT)
    async def bind_mobile(
        req_vo: AuthBindMobileReqVO,
        auth: AuthAdminAuthService = Depends(DiDependency(AuthAdminAuthService)),
        security: SecurityContext = Depends(DiDependency(SecurityContext)),
    ) -> Result[bool]:
        await auth.bind_mobile(int(security.require().account_id), req_vo)
        return Result.success(True)

    @staticmethod
    @auth_controller.get("/social-auth-redirect")
    @RoutePolicy.public()
    async def social_auth_redirect(
        response: Response,
        req_vo: AuthSocialAuthRedirectReqVO = Query(),
        clients: SocialClientService = Depends(DiDependency(SocialClientService)),
        workloads: SystemWorkloadService = Depends(DiDependency(SystemWorkloadService)),
        settings: SystemSettings = Depends(DiDependency(SystemSettings)),
        tenant: TenantSettings = Depends(DiDependency(TenantSettings)),
    ) -> Result[str | None]:
        binding = secrets.token_urlsafe(48)
        async with workloads.scope("system.auth", tenant.default_tenant_id):
            authorization = await clients.get_authorize_url(
                req_vo.type, 2, req_vo.redirect_uri, binding=binding
            )
        response.set_cookie(
            "system_social_binding",
            binding,
            max_age=authorization.expires_in,
            httponly=True,
            secure=settings.refresh_cookie_secure,
            samesite="lax",
            path="/admin-api/system",
        )
        return Result.success(authorization.url)

    @staticmethod
    @auth_controller.post("/websocket-ticket")
    @RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT)
    @AccessLogPolicy(enabled=False)
    async def websocket_ticket(
        tokens: OAuth2TokenService = Depends(DiDependency(OAuth2TokenService)),
        security: SecurityContext = Depends(DiDependency(SecurityContext)),
    ) -> Result[str]:
        return Result.success(await tokens.create_socket_ticket(security.require()))
