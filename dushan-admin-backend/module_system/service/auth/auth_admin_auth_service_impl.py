from __future__ import annotations

from typing import override

from framework.common.dates import DateUtils
from framework.common.enums import StatusEnum, UserTypeEnum
from framework.common.exception import ServiceException
from framework.starter_database.public import (
    transactional,
)
from framework.starter_di.public import (
    Inject,
    service,
)
from framework.starter_security.public import (
    PasswordEncoder,
)
from framework.starter_tenant.public import (
    TenantSettings,
)
from framework.starter_web.public import (
    RequestContext,
)
from module_system.api.logger.dto.login_log_create_req_dto import LoginLogCreateReqDTO
from module_system.api.sms.dto.code.code_sms_code_send_req_dto import SmsCodeSendReqDTO
from module_system.api.sms.dto.code.code_sms_code_use_req_dto import SmsCodeUseReqDTO
from module_system.api.social.dto.social_user_bind_req_dto import SocialUserBindReqDTO
from module_system.api.social.dto.social_user_resp_dto import SocialUserRespDTO
from module_system.config.system_settings import SystemSettings
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
from module_system.controller.admin.auth.vo.auth_social_login_req_vo import AuthSocialLoginReqVO
from module_system.controller.admin.user.vo.profile.profile_update_req_vo import (
    UserProfileUpdateReqVO,
)
from module_system.convert.auth.auth_convert import AuthConvert
from module_system.dal.mapper.auth.system_authentication_mapper import SystemAuthenticationMapper
from module_system.definitions.constants.error_code_constants import ErrorCodeConstants
from module_system.definitions.enums.logger.logger_login_result_enum import LoggerLoginResultEnum
from module_system.definitions.enums.logger.login_log_type_enum import LoginLogTypeEnum
from module_system.definitions.enums.sms.sms_scene_enum import SmsSceneEnum
from module_system.service.auth.auth_admin_auth_service import AuthAdminAuthService
from module_system.service.captcha.captcha_service import CaptchaService
from module_system.service.logger.login_log_service import LoginLogService
from module_system.service.oauth2.oauth2_client_service import OAuth2ClientService
from module_system.service.oauth2.oauth2_token_service import OAuth2TokenService
from module_system.service.permission.menu_service import MenuService
from module_system.service.permission.permission_service import PermissionService
from module_system.service.permission.role_service import RoleService
from module_system.service.sms.sms_code_service import SmsCodeService
from module_system.service.social.social_user_service import SocialUserService
from module_system.service.user.admin_user_service import AdminUserService


@service(interface=AuthAdminAuthService)
class AuthAdminAuthServiceImpl(AuthAdminAuthService):
    """管理后台认证 Service 实现类"""

    sms_code_service: SmsCodeService = Inject()
    user_service: AdminUserService = Inject()
    social_user_service: SocialUserService = Inject()
    login_log_service: LoginLogService = Inject()
    captcha_service: CaptchaService = Inject()
    oauth2_token_service: OAuth2TokenService = Inject()
    oauth2_client_service: OAuth2ClientService = Inject()
    permission_service: PermissionService = Inject()
    role_service: RoleService = Inject()
    menu_service: MenuService = Inject()
    date_utils: DateUtils = Inject()

    @override
    async def login(self, req_vo: AuthLoginReqVO) -> AuthLoginRespVO:
        await self._validate_captcha(req_vo)
        user = await self.authenticate(req_vo.username, req_vo.password)
        if req_vo.social_type is not None:
            social_bind_dto = SocialUserBindReqDTO(
                user_id=user.id,
                user_type=UserTypeEnum.ADMIN.code,
                type=req_vo.social_type,
                code=req_vo.social_code,
                state=req_vo.social_state,
            )
            await self.social_user_service.bind_social_user(social_bind_dto)
        return await self._create_token_after_login_success(
            user.id, req_vo.username, LoginLogTypeEnum.LOGIN_USERNAME.code, req_vo.client_id
        )

    @override
    async def send_sms_code(self, req_vo: AuthSmsSendReqVO) -> None:
        if not await self._do_validate_captcha(req_vo):
            raise ServiceException(ErrorCodeConstants.AUTH_REGISTER_CAPTCHA_CODE_ERROR)
        if req_vo.scene in (
            SmsSceneEnum.ADMIN_MEMBER_LOGIN.code,
            SmsSceneEnum.ADMIN_MEMBER_RESET_PASSWORD.code,
        ):
            if not await self.authentication.user_by_mobile(req_vo.mobile):
                raise ServiceException(ErrorCodeConstants.AUTH_MOBILE_NOT_EXISTS)
        elif req_vo.scene == SmsSceneEnum.ADMIN_MEMBER_UPDATE_MOBILE.code:
            if await self.authentication.user_by_mobile(req_vo.mobile):
                raise ServiceException(ErrorCodeConstants.USER_MOBILE_EXISTS, req_vo.mobile)
        sms_req_dto = SmsCodeSendReqDTO(
            mobile=req_vo.mobile,
            scene=req_vo.scene,
            create_ip=(RequestContext.current().client_ip or ""),
        )
        await self.sms_code_service.send_sms_code(sms_req_dto)

    @override
    async def sms_login(self, req_vo: AuthSmsLoginReqVO) -> AuthLoginRespVO:
        sms_use_dto = SmsCodeUseReqDTO(
            mobile=req_vo.mobile,
            code=req_vo.code,
            scene=SmsSceneEnum.ADMIN_MEMBER_LOGIN.code,
            used_ip=(RequestContext.current().client_ip or ""),
        )
        await self.sms_code_service.use_sms_code(sms_use_dto)
        user = await self.authentication.user_by_mobile(req_vo.mobile)
        if not user:
            raise ServiceException(ErrorCodeConstants.USER_NOT_EXISTS)
        return await self._create_token_after_login_success(
            user.id, req_vo.mobile, LoginLogTypeEnum.LOGIN_MOBILE.code, req_vo.client_id
        )

    @override
    async def bind_mobile(self, user_id: int, req_vo: AuthBindMobileReqVO) -> None:
        user = await self.user_service.get_user(user_id)
        if not user:
            raise ServiceException(ErrorCodeConstants.USER_NOT_EXISTS)
        sms_use_dto = SmsCodeUseReqDTO(
            code=req_vo.code,
            mobile=req_vo.mobile,
            scene=SmsSceneEnum.ADMIN_MEMBER_UPDATE_MOBILE.code,
            used_ip=(RequestContext.current().client_ip or ""),
        )
        await self.sms_code_service.use_sms_code(sms_use_dto)
        await self.user_service.update_user_profile(
            user_id, UserProfileUpdateReqVO(mobile=req_vo.mobile)
        )

    @override
    async def social_login(self, req_vo: AuthSocialLoginReqVO) -> AuthLoginRespVO:
        social_user: SocialUserRespDTO = await self.social_user_service.get_social_user_by_code(
            UserTypeEnum.ADMIN.code, req_vo.type, req_vo.code, req_vo.state
        )
        if not social_user or not social_user.user_id:
            raise ServiceException(ErrorCodeConstants.AUTH_THIRD_LOGIN_NOT_BIND)
        user = await self.authentication.user_by_id(social_user.user_id)
        if not user:
            raise ServiceException(ErrorCodeConstants.USER_NOT_EXISTS)
        return await self._create_token_after_login_success(
            user.id, user.username, LoginLogTypeEnum.LOGIN_SOCIAL.code, req_vo.client_id
        )

    @override
    async def refresh_token(self, refresh_token: str, client_id: str) -> AuthLoginRespVO:
        access_token = await self.oauth2_token_service.refresh_access_token(
            refresh_token, client_id
        )
        return AuthConvert.convert_oauth_to_auth_login_resp(access_token, self.date_utils)

    @override
    async def logout(self, token: str, log_type: int) -> None:
        access_token_data = await self.oauth2_token_service.remove_access_token(token)
        if not access_token_data:
            return
        await self._create_logout_log(
            access_token_data.user_id, access_token_data.user_type, log_type
        )

    @override
    async def register(self, req: AuthRegisterReqVO) -> AuthLoginRespVO:
        await self._validate_captcha_for_register(req)
        user_id = await self.user_service.register_user(req)
        return await self._create_token_after_login_success(
            user_id, req.username, LoginLogTypeEnum.LOGIN_USERNAME.code, req.client_id
        )

    @override
    @transactional
    async def reset_password(self, req: AuthResetPasswordReqVO) -> None:
        user = await self.authentication.user_by_mobile(req.mobile)
        if not user:
            raise ServiceException(ErrorCodeConstants.USER_MOBILE_NOT_EXISTS)
        sms_req_dto = SmsCodeUseReqDTO(
            code=req.code,
            mobile=req.mobile,
            scene=SmsSceneEnum.ADMIN_MEMBER_RESET_PASSWORD.code,
            used_ip=(RequestContext.current().client_ip or ""),
        )
        await self.sms_code_service.use_sms_code(sms_req_dto)
        await self.user_service.change_password(user.id, req.password)

    @override
    async def get_permission_info(self, user_id: int) -> AuthPermissionInfoRespVO | None:
        """获取登录用户的权限信息"""
        user = await self.user_service.get_user(user_id)
        if not user:
            return None
        role_ids: set[int] = await self.permission_service.get_user_role_id_list_by_user_id(user_id)
        if not role_ids:
            return AuthConvert.convert_permission_info(user, [], [])
        roles = await self.role_service.get_role_list_by_ids(role_ids)
        roles = [role for role in roles if role.status == StatusEnum.ENABLE.code]
        menu_ids: set[int] = await self.permission_service.get_role_menu_list_by_role_ids(role_ids)
        menu_list = await self.menu_service.get_menu_list_by_ids(menu_ids)
        menu_list = await self.menu_service.filter_disable_menus(menu_list)
        return AuthConvert.convert_permission_info(user, roles, menu_list)

    async def _validate_captcha(self, req_vo: AuthLoginReqVO) -> None:
        """登录验证码校验"""
        if not await self._do_validate_captcha(req_vo):
            await self._create_login_log(
                None,
                req_vo.username,
                LoginLogTypeEnum.LOGIN_USERNAME.code,
                LoggerLoginResultEnum.CAPTCHA_CODE_ERROR.code,
            )
            raise ServiceException(ErrorCodeConstants.AUTH_LOGIN_CAPTCHA_CODE_ERROR)

    async def _get_username(self, user_id: int) -> str | None:
        """获取用户名"""
        if not user_id:
            return None
        user = await self.user_service.get_user(user_id)
        return user.username if user else None

    settings: SystemSettings = Inject()
    tenant_settings: TenantSettings = Inject()
    authentication: SystemAuthenticationMapper = Inject()
    passwords: PasswordEncoder = Inject()

    async def authenticate(self, username: str, password: str):
        user = await self.authentication.user_by_username(username)
        log_type = LoginLogTypeEnum.LOGIN_USERNAME.code
        if user is None or not await self.passwords.verify(password, user.password):
            await self._create_login_log(
                None if user is None else user.id,
                username,
                log_type,
                LoggerLoginResultEnum.BAD_CREDENTIALS.code,
            )
            raise ServiceException(ErrorCodeConstants.AUTH_LOGIN_BAD_CREDENTIALS)
        if user.status != StatusEnum.ENABLE.code:
            await self._create_login_log(
                user.id, username, log_type, LoggerLoginResultEnum.USER_DISABLED.code
            )
            raise ServiceException(ErrorCodeConstants.AUTH_LOGIN_USER_DISABLED)
        return user

    async def _do_validate_captcha(self, req_vo):
        return await self.captcha_service.verification(req_vo)

    async def _validate_captcha_for_register(self, req):
        await self.captcha_service.verification(req, purpose="register")

    async def _create_token_after_login_success(self, user_id, username, log_type, client_id):
        client_id = self.settings.default_client_id if client_id is None else client_id
        client = await self.oauth2_client_service.validate_client(client_id)
        access_token = await self.oauth2_token_service.create_access_token(
            user_id, UserTypeEnum.ADMIN.code, client_id, client.scopes
        )
        await self._create_login_log(
            user_id, username, log_type, LoggerLoginResultEnum.SUCCESS.code
        )
        return AuthConvert.convert_oauth_to_auth_login_resp(access_token, self.date_utils)

    async def _create_login_log(self, user_id, username, log_type, login_result):
        request = RequestContext.current()
        log = LoginLogCreateReqDTO(
            log_type=log_type,
            trace_id=request.request_id,
            user_id=0 if user_id is None else user_id,
            user_type=UserTypeEnum.ADMIN.code,
            username=username,
            user_agent=request.connection.headers.get("user-agent", "")[:512],
            user_ip=request.client_ip or "",
            result=login_result,
            creator="" if user_id is None else str(user_id),
            tenant_id=self.tenant_settings.default_tenant_id,
        )
        await self.login_log_service.create_login_log(log)
        if user_id is not None and login_result == LoggerLoginResultEnum.SUCCESS.code:
            await self.user_service.update_user_login(user_id, request.client_ip or "")

    async def _create_logout_log(self, user_id, user_type, log_type):
        request = RequestContext.current()
        user = (
            await self.authentication.user_by_id(user_id)
            if user_type == UserTypeEnum.ADMIN.code
            else None
        )
        log = LoginLogCreateReqDTO(
            log_type=log_type,
            trace_id=request.request_id,
            user_id=user_id,
            user_type=user_type,
            username="" if user is None else user.username,
            user_agent=request.connection.headers.get("user-agent", "")[:512],
            user_ip=request.client_ip or "",
            result=LoggerLoginResultEnum.SUCCESS.code,
            creator=str(user_id),
            tenant_id=self.tenant_settings.default_tenant_id,
        )
        await self.login_log_service.create_login_log(log)
