from __future__ import annotations

import hashlib
import hmac
import math
import secrets
from datetime import datetime, timezone
from typing import override

from loguru import logger
from sqlalchemy import select

from framework.common.dates import DateUtils
from framework.common.enums import StatusEnum, UserTypeEnum
from framework.common.exception import BaseBusinessException, ServiceException
from framework.starter_cache.public import CacheHandler, DistributedLock
from framework.starter_database.public import (
    SessionProvider,
    transactional,
)
from framework.starter_di.public import (
    Inject,
    service,
)
from framework.starter_security.public import (
    LoginSession,
    PasswordEncoder,
    SecurityErrorCodes,
    SecurityException,
)
from framework.starter_tenant.public import (
    TenantContext,
)
from framework.starter_web.public import (
    RequestContext,
)
from module_system.api.logger.dto.login_log_create_req_dto import LoginLogCreateReqDTO
from module_system.api.sms.dto.code.code_sms_code_send_req_dto import SmsCodeSendReqDTO
from module_system.api.sms.dto.code.code_sms_code_use_req_dto import SmsCodeUseReqDTO
from module_system.api.social.dto.social_user_bind_req_dto import SocialUserBindReqDTO
from module_system.api.social.dto.social_user_resp_dto import SocialUserRespDTO
from module_system.config.password_reset_settings import PasswordResetSettings
from module_system.config.system_settings import SystemSettings
from module_system.controller.admin.auth.vo.auth_bind_mobile_req_vo import AuthBindMobileReqVO
from module_system.controller.admin.auth.vo.auth_login_req_vo import AuthLoginReqVO
from module_system.controller.admin.auth.vo.auth_login_resp_vo import AuthLoginRespVO
from module_system.controller.admin.auth.vo.auth_permission_info_resp_vo import (
    AuthPermissionInfoRespVO,
)
from module_system.controller.admin.auth.vo.auth_recovery_send_req_vo import AuthRecoverySendReqVO
from module_system.controller.admin.auth.vo.auth_register_req_vo import AuthRegisterReqVO
from module_system.controller.admin.auth.vo.auth_reset_password_req_vo import AuthResetPasswordReqVO
from module_system.controller.admin.auth.vo.auth_sms_login_req_vo import AuthSmsLoginReqVO
from module_system.controller.admin.auth.vo.auth_sms_send_req_vo import AuthSmsSendReqVO
from module_system.controller.admin.auth.vo.auth_social_login_req_vo import AuthSocialLoginReqVO
from module_system.controller.admin.user.vo.profile.profile_update_req_vo import (
    UserProfileUpdateReqVO,
)
from module_system.convert.auth.auth_convert import AuthConvert
from module_system.dal.cache.cache_key_constants import SystemCacheKeys
from module_system.dal.dataobject.user.admin_user_do import AdminUserDO
from module_system.dal.mapper.auth.system_authentication_mapper import SystemAuthenticationMapper
from module_system.definitions.constants.error_code_constants import ErrorCodeConstants
from module_system.definitions.enums.logger.logger_login_result_enum import LoggerLoginResultEnum
from module_system.definitions.enums.logger.login_log_type_enum import LoginLogTypeEnum
from module_system.definitions.enums.sms.sms_scene_enum import SmsSceneEnum
from module_system.service.auth.auth_admin_auth_service import AuthAdminAuthService
from module_system.service.auth.bo.email_reset_state import EmailResetState
from module_system.service.captcha.captcha_service import CaptchaService
from module_system.service.logger.login_log_service import LoginLogService
from module_system.service.mail.bo.mail_dispatch_bo import MailDispatchBO
from module_system.service.mail.mail_send_service import MailSendService
from module_system.service.oauth2.oauth2_client_service import OAuth2ClientService
from module_system.service.oauth2.oauth2_token_service import OAuth2TokenService
from module_system.service.permission.menu_service import MenuService
from module_system.service.permission.permission_service import PermissionService
from module_system.service.permission.role_service import RoleService
from module_system.service.sms.sms_code_service import SmsCodeService
from module_system.service.social.social_user_service import SocialUserService
from module_system.service.user.admin_user_service import AdminUserService
from module_system.service.workload.system_workload_service import SystemWorkloadService


@service(interface=AuthAdminAuthService)
class AuthAdminAuthServiceImpl(AuthAdminAuthService):
    """管理后台认证 Service 实现类"""

    sms_code_service: SmsCodeService = Inject()
    workloads: SystemWorkloadService = Inject()
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
    settings: SystemSettings = Inject()
    tenant: TenantContext = Inject()
    authentication: SystemAuthenticationMapper = Inject()
    passwords: PasswordEncoder = Inject()
    reset_settings: PasswordResetSettings = Inject()
    mail_sender: MailSendService = Inject()
    cache: CacheHandler = Inject()
    locks: DistributedLock = Inject()
    database: SessionProvider = Inject()

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
    async def send_sms_code(self, req_vo: AuthSmsSendReqVO) -> int:
        purpose = (
            "password_reset"
            if req_vo.scene == SmsSceneEnum.ADMIN_MEMBER_RESET_PASSWORD.code
            else "login"
        )
        if not await self.captcha_service.verification(req_vo, purpose=purpose):
            raise ServiceException(ErrorCodeConstants.AUTH_REGISTER_CAPTCHA_CODE_ERROR)
        deliver = True
        if req_vo.scene in (
            SmsSceneEnum.ADMIN_MEMBER_LOGIN.code,
            SmsSceneEnum.ADMIN_MEMBER_RESET_PASSWORD.code,
        ):
            deliver = (
                await self.authentication.user_by_mobile(
                    req_vo.mobile, self.tenant.get_required_tenant_id()
                )
                is not None
            )
        elif req_vo.scene == SmsSceneEnum.ADMIN_MEMBER_UPDATE_MOBILE.code:
            deliver = (
                await self.authentication.user_by_mobile(
                    req_vo.mobile, self.tenant.get_required_tenant_id()
                )
                is None
            )
        sms_req_dto = SmsCodeSendReqDTO(
            mobile=req_vo.mobile,
            scene=req_vo.scene,
            create_ip=(RequestContext.current().client_ip or ""),
        )
        return await self.sms_code_service.send_sms_code(sms_req_dto, deliver=deliver)

    @override
    async def qr_login(self, identity: LoginSession) -> AuthLoginRespVO:
        user = await self.authentication.user_by_id(
            int(identity.account_id), self.tenant.get_required_tenant_id()
        )
        if user is None or user.status != StatusEnum.ENABLE.code:
            raise ServiceException(ErrorCodeConstants.AUTH_LOGIN_USER_DISABLED)
        return await self._create_token_after_login_success(
            user.id,
            user.username,
            LoginLogTypeEnum.LOGIN_QRCODE.code,
            None,
            scopes=sorted(identity.scopes),
        )

    @override
    async def sms_login(self, req_vo: AuthSmsLoginReqVO) -> AuthLoginRespVO:
        sms_use_dto = SmsCodeUseReqDTO(
            mobile=req_vo.mobile,
            code=req_vo.code,
            scene=SmsSceneEnum.ADMIN_MEMBER_LOGIN.code,
            used_ip=(RequestContext.current().client_ip or ""),
        )
        await self.sms_code_service.use_sms_code(sms_use_dto)
        user = await self.authentication.user_by_mobile(
            req_vo.mobile, self.tenant.get_required_tenant_id()
        )
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
        user = await self.authentication.user_by_id(
            social_user.user_id, self.tenant.get_required_tenant_id()
        )
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
        tenant_id = await self.oauth2_token_service.get_token_tenant(token, refresh=False)
        if tenant_id is None:
            return
        async with self.workloads.scope("system.auth.revoke", tenant_id):
            access_token_data = await self.oauth2_token_service.remove_access_token(token)
            if access_token_data is not None:
                await self._create_logout_log(
                    access_token_data.user_id, access_token_data.user_type, log_type
                )

    @override
    async def register(self, req: AuthRegisterReqVO) -> AuthLoginRespVO:
        if not self.settings.user_register_enabled:
            raise ServiceException(ErrorCodeConstants.USER_REGISTER_DISABLED)
        await self._validate_captcha_for_register(req)
        user_id = await self.user_service.register_user(req)
        return await self._create_token_after_login_success(
            user_id, req.username, LoginLogTypeEnum.LOGIN_USERNAME.code, req.client_id
        )

    @override
    async def reset_password(self, req: AuthResetPasswordReqVO) -> None:
        if req.channel == "email":
            await self._reset_email_password(req.email, req.code, req.password)
        else:
            await self._reset_sms_password(req)

    @override
    async def send_recovery_code(self, req: AuthRecoverySendReqVO) -> int:
        if not await self.captcha_service.verification(req, purpose="password_reset"):
            raise ServiceException(ErrorCodeConstants.AUTH_LOGIN_CAPTCHA_CODE_ERROR)
        if req.channel == "email":
            return await self._send_email_reset_code(req.email)
        user = await self.authentication.user_by_mobile(
            req.mobile, self.tenant.get_required_tenant_id()
        )
        return await self.sms_code_service.send_sms_code(
            SmsCodeSendReqDTO(
                mobile=req.mobile,
                scene=SmsSceneEnum.ADMIN_MEMBER_RESET_PASSWORD.code,
                create_ip=RequestContext.current().client_ip or "",
            ),
            deliver=user is not None,
        )

    @transactional
    async def _reset_sms_password(self, req: AuthResetPasswordReqVO) -> None:
        user = await self.authentication.user_by_mobile(
            req.mobile, self.tenant.get_required_tenant_id()
        )
        sms_req_dto = SmsCodeUseReqDTO(
            code=req.code,
            mobile=req.mobile,
            scene=SmsSceneEnum.ADMIN_MEMBER_RESET_PASSWORD.code,
            used_ip=(RequestContext.current().client_ip or ""),
        )
        try:
            await self.sms_code_service.use_sms_code(sms_req_dto)
        except ServiceException as error:
            if error.error_code in {
                ErrorCodeConstants.SMS_CODE_NOT_FOUND,
                ErrorCodeConstants.SMS_CODE_NOT_CORRECT,
                ErrorCodeConstants.SMS_CODE_EXPIRED,
                ErrorCodeConstants.SMS_CODE_USED,
                ErrorCodeConstants.SMS_CODE_ATTEMPTS_EXCEEDED,
            }:
                raise ServiceException(ErrorCodeConstants.AUTH_RESET_CODE_INVALID) from error
            raise
        if user is None:
            raise ServiceException(ErrorCodeConstants.AUTH_RESET_CODE_INVALID)
        await self.user_service.change_password(user.id, req.password)

    @staticmethod
    def _email_identifier(email: str) -> str:
        return hashlib.sha256(email.casefold().encode()).hexdigest()

    def _email_reset_lock(self, identifier: str):
        return self.locks.with_lock(
            f"system:email-reset:{self.tenant.get_required_tenant_id()}:{identifier}",
            client_name="default",
            lease_seconds=45,
            wait_seconds=5,
            critical_section_timeout_seconds=30,
        )

    def _email_code_digest(self, identifier: str, code: str) -> str:
        key = self.settings.message_signing_key
        if key is None or len(key.get_secret_value()) < 32:
            raise SecurityException(SecurityErrorCodes.CONFIGURATION)
        message = f"email-password-reset:{self.tenant.get_required_tenant_id()}:{identifier}:{code}"
        return hmac.new(
            key.get_secret_value().encode(), message.encode(), hashlib.sha256
        ).hexdigest()

    async def _send_email_reset_code(self, email: str) -> int:
        """未登记邮箱同样返回位数，不暴露账号是否存在；缓存只保存验证码摘要。"""
        user = await self.authentication.user_by_email(email, self.tenant.get_required_tenant_id())
        identifier = self._email_identifier(email if user is None else user.email)
        async with self._email_reset_lock(identifier):
            now = datetime.now(timezone.utc)
            cached = await self.cache.get(SystemCacheKeys.EMAIL_PASSWORD_RESET, identifier)
            count = 1
            if cached.hit:
                previous = EmailResetState.model_validate(cached.value)
                if now.timestamp() - previous.issued_at < self.reset_settings.resend_seconds:
                    raise ServiceException(ErrorCodeConstants.AUTH_RESET_SEND_LIMIT)
                issued = datetime.fromtimestamp(previous.issued_at, timezone.utc)
                if self.date_utils.to_timezone(issued).date() == self.date_utils.now().date():
                    if previous.daily_count >= self.reset_settings.max_daily:
                        raise ServiceException(ErrorCodeConstants.AUTH_RESET_SEND_LIMIT)
                    count = previous.daily_count + 1
            code = str(secrets.randbelow(1_000_000)).zfill(6)
            state = EmailResetState(
                code_digest=self._email_code_digest(identifier, code),
                user_id=None if user is None else user.id,
                credential_revision=None if user is None else user.credential_revision,
                issued_at=now.timestamp(),
                expires_at=now.timestamp() + self.reset_settings.expire_seconds,
                attempts=0,
                daily_count=count,
            )
            await self.cache.set(
                SystemCacheKeys.EMAIL_PASSWORD_RESET,
                identifier,
                state.model_dump(mode="json", by_alias=False),
            )
            if user is not None:
                try:
                    await self.mail_sender.send_single_mail(
                        MailDispatchBO(
                            mail=user.email,
                            user_id=user.id,
                            user_type=UserTypeEnum.ADMIN.code,
                            template_code=self.reset_settings.mail_template_code,
                            template_params={
                                "code": code,
                                "minutes": math.ceil(self.reset_settings.expire_seconds / 60),
                            },
                            require_delivery=True,
                        )
                    )
                except (BaseBusinessException, TimeoutError) as error:
                    logger.error(
                        "找回密码邮件投递未完成 error_type={} code={}",
                        type(error).__name__,
                        error.error_code.code if isinstance(error, BaseBusinessException) else None,
                    )
        return 6

    async def _reset_email_password(self, email: str, code: str, password: str) -> None:
        """锁内核对验证码状态，事务内按行锁复核凭据版本；锁必须包住事务提交。"""
        user = await self.authentication.user_by_email(email, self.tenant.get_required_tenant_id())
        identifier = self._email_identifier(email if user is None else user.email)
        async with self._email_reset_lock(identifier):
            cached = await self.cache.get(SystemCacheKeys.EMAIL_PASSWORD_RESET, identifier)
            if not cached.hit:
                raise ServiceException(ErrorCodeConstants.AUTH_RESET_CODE_INVALID)
            state = EmailResetState.model_validate(cached.value)
            now = datetime.now(timezone.utc).timestamp()
            if now >= state.expires_at or state.attempts >= self.reset_settings.max_attempts:
                raise ServiceException(ErrorCodeConstants.AUTH_RESET_CODE_INVALID)
            state = state.model_copy(update={"attempts": state.attempts + 1})
            await self.cache.set(
                SystemCacheKeys.EMAIL_PASSWORD_RESET,
                identifier,
                state.model_dump(mode="json", by_alias=False),
                ttl_seconds=math.ceil(state.issued_at + 86400 - now),
            )
            if (
                not hmac.compare_digest(
                    state.code_digest, self._email_code_digest(identifier, code)
                )
                or user is None
                or state.user_id != user.id
                or state.credential_revision != user.credential_revision
            ):
                raise ServiceException(ErrorCodeConstants.AUTH_RESET_CODE_INVALID)
            async with self.database.transaction() as session:
                current = (
                    await session.scalars(
                        select(AdminUserDO).where(AdminUserDO.id == state.user_id).with_for_update()
                    )
                ).one_or_none()
                if (
                    current is None
                    or current.email is None
                    or current.email.casefold() != user.email.casefold()
                    or current.credential_revision != state.credential_revision
                ):
                    raise ServiceException(ErrorCodeConstants.AUTH_RESET_CODE_INVALID)
                # 提交后的凭据版本变化使此码不可复用，保留缓存以继续执行发送频率/日限额。
                await self.user_service.change_password(current.id, password)

    @override
    async def get_permission_info(self, user_id: int) -> AuthPermissionInfoRespVO | None:
        """获取登录用户的权限信息"""
        user = await self.user_service.get_user(user_id)
        if not user:
            return None
        role_ids: set[int] = await self.permission_service.get_user_role_id_list_by_user_id(user_id)
        if not role_ids:
            return AuthConvert.convert_permission_info(user, [], [])
        roles = await self.permission_service.get_enable_user_role_list_by_user_id_from_cache(
            user_id
        )
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

    async def authenticate(self, username: str, password: str):
        user = await self.authentication.user_by_username(
            username, self.tenant.get_required_tenant_id()
        )
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
        if not await self.captcha_service.verification(req, purpose="register"):
            raise ServiceException(ErrorCodeConstants.AUTH_REGISTER_CAPTCHA_CODE_ERROR)

    async def _create_token_after_login_success(
        self, user_id, username, log_type, client_id, *, scopes=None
    ):
        client_id = self.settings.default_client_id if client_id is None else client_id
        client = await self.oauth2_client_service.validate_client(client_id)
        access_token = await self.oauth2_token_service.create_access_token(
            user_id, UserTypeEnum.ADMIN.code, client_id, client.scopes if scopes is None else scopes
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
            tenant_id=self.tenant.get_required_tenant_id(),
        )
        await self.login_log_service.create_login_log(log)
        if user_id is not None and login_result == LoggerLoginResultEnum.SUCCESS.code:
            await self.user_service.update_user_login(user_id, request.client_ip or "")

    async def _create_logout_log(self, user_id, user_type, log_type):
        request = RequestContext.current()
        user = (
            await self.authentication.user_by_id(user_id, self.tenant.get_required_tenant_id())
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
            tenant_id=self.tenant.get_required_tenant_id(),
        )
        await self.login_log_service.create_login_log(log)
