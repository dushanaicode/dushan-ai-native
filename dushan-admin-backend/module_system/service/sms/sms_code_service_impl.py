from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timezone

from loguru import logger

from framework.common.dates import DateUtils
from framework.common.enums import ApplicationEnvironmentEnum, UserTypeEnum
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
from framework.starter_tenant.public import (
    TenantContext,
)
from module_system.dal.cache.cache_key_constants import SystemCacheKeys
from module_system.dal.dataobject.sms.sms_code_do import SmsCodeDO
from module_system.dal.mapper.sms.sms_code_mapper import SmsCodeMapper
from module_system.definitions.constants.error_code_constants import ErrorCodeConstants
from module_system.definitions.constants.sms_code_constants import SmsCodeConstants
from module_system.definitions.enums.sms.sms_scene_enum import SmsSceneEnum
from module_system.framework.sms.config.sms_captcha_settings import SmsCaptchaSettings
from module_system.service.sms.bo.sms_dispatch_bo import SmsDispatchBO
from module_system.service.sms.sms_code_service import SmsCodeService
from module_system.service.sms.sms_send_service import SmsSendService


@service(interface=SmsCodeService)
class SmsCodeServiceImpl(SmsCodeService):
    mapper: SmsCodeMapper = Inject()
    sender: SmsSendService = Inject()
    settings: SmsCaptchaSettings = Inject()
    database: SessionProvider = Inject()
    locks: DistributedLock = Inject()
    cache: CacheHandler = Inject()
    tenant: TenantContext = Inject()
    dates: DateUtils = Inject()
    environment: ApplicationEnvironmentEnum = Inject()

    def _debug_allowed(self, mobile: str, scene: int) -> bool:
        return (
            self.environment is ApplicationEnvironmentEnum.DEVELOPMENT
            and self.settings.debug_enabled
            and mobile in self.settings.debug_mobiles
            and scene == SmsSceneEnum.ADMIN_MEMBER_LOGIN.code
        )

    def _normal_code(self) -> str:
        reserved = int(SmsCodeConstants.DEBUG_CODE)
        excludes_debug = self.settings.begin_code <= reserved <= self.settings.end_code
        count = self.settings.end_code - self.settings.begin_code + 1 - int(excludes_debug)
        number = self.settings.begin_code + secrets.randbelow(count)
        if excludes_debug and number >= reserved:
            number += 1
        return str(number).zfill(len(str(self.settings.end_code)))

    async def send_sms_code(self, req_dto, *, deliver: bool = True) -> int:
        scene = SmsSceneEnum.get_by_code(req_dto.scene)
        if scene is None:
            raise ServiceException(ErrorCodeConstants.SMS_SCENE_NOT_FOUND, req_dto.scene)
        identifier = hashlib.sha256(req_dto.mobile.encode()).hexdigest()
        async with self.locks.with_lock(
            f"system:sms-code:{self.tenant.get_required_tenant_id()}:{identifier}",
            client_name="default",
            lease_seconds=45,
            wait_seconds=5,
            critical_section_timeout_seconds=30,
        ):
            async with self.database.transaction():
                last = await self.mapper.select_last_by_mobile(req_dto.mobile, None)
                now = datetime.now(timezone.utc).replace(tzinfo=None)
                same_day = (
                    last is not None
                    and self.dates.to_timezone(last.create_time.replace(tzinfo=timezone.utc)).date()
                    == self.dates.now().date()
                )
                if (
                    last is not None
                    and (now - last.create_time).total_seconds() < self.settings.send_frequency
                ):
                    raise ServiceException(ErrorCodeConstants.SMS_CODE_SEND_TOO_FAST)
                if same_day and last.today_index >= self.settings.send_maximum_quantity_per_day:
                    raise ServiceException(
                        ErrorCodeConstants.SMS_CODE_EXCEED_SEND_MAXIMUM_QUANTITY_PER_DAY
                    )
                debug = self._debug_allowed(req_dto.mobile, req_dto.scene)
                code = SmsCodeConstants.DEBUG_CODE if debug else self._normal_code()
                await self.mapper.insert(
                    SmsCodeDO(
                        mobile=req_dto.mobile,
                        code=code,
                        scene=req_dto.scene,
                        today_index=last.today_index + 1 if same_day else 1,
                        create_ip=req_dto.create_ip,
                        used=False,
                    )
                )
                dispatch = SmsDispatchBO(
                    require_delivery=True,
                    mobile=req_dto.mobile,
                    user_id=None,
                    user_type=UserTypeEnum.ADMIN.code,
                    template_code=scene.template_code,
                    template_params={"code": code},
                )
            # 公开验证码请求先统一登记频率/日限额，再决定投递，避免相邻入口泄露绑定状态。
            if not debug and deliver:
                try:
                    await self.sender.send_single_sms(dispatch)
                except (BaseBusinessException, TimeoutError) as error:
                    logger.error(
                        "验证码短信投递未完成 error_type={} code={}",
                        type(error).__name__,
                        error.error_code.code if isinstance(error, BaseBusinessException) else None,
                    )
            return len(code)

    async def _validate(self, mobile, code, scene):
        """只校验该手机号在此场景下的最新一条验证码，每次比对前先原子占用一次校验次数。

        8888 从不作为正常码生成：当前配置不允许调试时直接拒绝，不消耗真实验证码的次数。
        比对在应用内按字节进行，不受数据库排序规则把尾随空格或全角数字视为相等的影响。
        """
        if code == SmsCodeConstants.DEBUG_CODE and not self._debug_allowed(mobile, scene):
            raise ServiceException(ErrorCodeConstants.SMS_CODE_NOT_CORRECT)
        record = await self.mapper.select_last_by_mobile(mobile, scene)
        if record is None:
            raise ServiceException(ErrorCodeConstants.SMS_CODE_NOT_FOUND)
        if record.code == SmsCodeConstants.DEBUG_CODE and not self._debug_allowed(mobile, scene):
            raise ServiceException(ErrorCodeConstants.SMS_CODE_NOT_CORRECT)
        if (
            datetime.now(timezone.utc).replace(tzinfo=None) - record.create_time
        ).total_seconds() >= self.settings.expire_times:
            raise ServiceException(ErrorCodeConstants.SMS_CODE_EXPIRED)
        if record.used:
            raise ServiceException(ErrorCodeConstants.SMS_CODE_USED)
        attempts = await self.cache.eval_atomic(
            SystemCacheKeys.SMS_CODE_ATTEMPTS,
            (str(record.id),),
            SmsCodeConstants.ATTEMPT_SCRIPT,
            (self.settings.expire_times,),
        )
        if attempts > self.settings.max_attempts:
            raise ServiceException(ErrorCodeConstants.SMS_CODE_ATTEMPTS_EXCEEDED)
        if not hmac.compare_digest(record.code.encode(), code.encode()):
            raise ServiceException(ErrorCodeConstants.SMS_CODE_NOT_CORRECT)
        return record

    @transactional
    async def use_sms_code(self, req_dto) -> None:
        record = await self._validate(req_dto.mobile, req_dto.code, req_dto.scene)
        changed = await self.mapper.update_by_condition(
            {
                "used": True,
                "used_time": datetime.now(timezone.utc).replace(tzinfo=None),
                "used_ip": req_dto.used_ip,
            },
            SmsCodeDO.id == record.id,
            SmsCodeDO.used.is_(False),
        )
        if changed != 1:
            raise ServiceException(ErrorCodeConstants.SMS_CODE_USED)

    async def validate_sms_code(self, req_dto) -> None:
        await self._validate(req_dto.mobile, req_dto.code, req_dto.scene)
