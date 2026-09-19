from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone

from framework.common.dates import DateUtils
from framework.common.enums import UserTypeEnum
from framework.common.exception import ServiceException
from framework.starter_cache.public import DistributedLock
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
from module_system.dal.dataobject.sms.sms_code_do import SmsCodeDO
from module_system.dal.mapper.sms.sms_code_mapper import SmsCodeMapper
from module_system.definitions.constants.error_code_constants import ErrorCodeConstants
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
    tenant: TenantContext = Inject()
    dates: DateUtils = Inject()

    async def send_sms_code(self, req_dto) -> None:
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
                last = await self.mapper.select_last_by_mobile(req_dto.mobile, None, None)
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
                number = self.settings.begin_code + secrets.randbelow(
                    self.settings.end_code - self.settings.begin_code + 1
                )
                code = str(number).zfill(len(str(self.settings.end_code)))
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
                await self.sender.send_single_sms(
                    SmsDispatchBO(
                        mobile=req_dto.mobile,
                        user_id=None,
                        user_type=UserTypeEnum.ADMIN.code,
                        template_code=scene.template_code,
                        template_params={"code": code},
                    )
                )

    async def _validate(self, mobile, code, scene):
        record = await self.mapper.select_last_by_mobile(mobile, code, scene)
        if record is None:
            raise ServiceException(ErrorCodeConstants.SMS_CODE_NOT_FOUND)
        if (
            datetime.now(timezone.utc).replace(tzinfo=None) - record.create_time
        ).total_seconds() >= self.settings.expire_times:
            raise ServiceException(ErrorCodeConstants.SMS_CODE_EXPIRED)
        if record.used:
            raise ServiceException(ErrorCodeConstants.SMS_CODE_USED)
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
