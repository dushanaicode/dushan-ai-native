from __future__ import annotations

from datetime import datetime, timezone
from typing import override

from framework.common.dates import DateUtils
from framework.common.page import PageResult
from framework.starter_database.public import (
    transactional,
)
from framework.starter_di.public import (
    Inject,
    service,
)
from module_system.controller.admin.sms.vo.log.log_page_req_vo import SmsLogPageReqVO
from module_system.dal.dataobject.sms.sms_log_do import SmsLogDO
from module_system.dal.mapper.sms.sms_log_mapper import SmsLogMapper
from module_system.definitions.enums.sms.sms_receive_status_enum import SmsReceiveStatusEnum
from module_system.definitions.enums.sms.sms_send_status_enum import SmsSendStatusEnum
from module_system.service.sms.bo.sms_log_create_bo import SmsLogCreateBO
from module_system.service.sms.bo.sms_receive_result_bo import SmsReceiveResultBO
from module_system.service.sms.bo.sms_send_result_bo import SmsSendResultBO
from module_system.service.sms.sms_log_service import SmsLogService


@service(interface=SmsLogService)
class SmsLogServiceImpl(SmsLogService):
    sms_log_mapper: SmsLogMapper = Inject()
    date_utils: DateUtils = Inject()

    @override
    @transactional
    async def create_sms_log(self, req: SmsLogCreateBO) -> int:
        send_status = SmsSendStatusEnum.INIT.code if req.is_send else SmsSendStatusEnum.IGNORE.code
        log_obj = SmsLogDO(
            mobile=req.mobile,
            user_id=req.user_id,
            user_type=req.user_type,
            template_id=req.template.id,
            template_code=req.template.code,
            template_type=req.template.type,
            template_content=req.template_content,
            template_params=req.template_params,
            api_template_id=req.template.api_template_id,
            channel_id=req.template.channel_id,
            channel_code=req.template.channel_code,
            send_status=send_status,
            receive_status=SmsReceiveStatusEnum.INIT.code,
        )
        await self.sms_log_mapper.insert(log_obj)
        return log_obj.id

    @override
    @transactional
    async def update_sms_send_result(self, req: SmsSendResultBO) -> None:
        send_status = (
            SmsSendStatusEnum.SUCCESS.code if req.success else SmsSendStatusEnum.FAILURE.code
        )
        update_obj = SmsLogDO(
            id=req.id,
            send_status=send_status,
            send_time=datetime.now(timezone.utc).replace(tzinfo=None),
            api_send_code=req.api_send_code,
            api_send_msg=req.api_send_msg,
            api_request_id=req.api_request_id,
            api_serial_no=req.api_serial_no,
        )
        await self.sms_log_mapper.update_by_id(update_obj)

    @override
    @transactional
    async def update_sms_receive_result(self, req: SmsReceiveResultBO) -> None:
        receive_status = (
            SmsReceiveStatusEnum.SUCCESS.code if req.success else SmsReceiveStatusEnum.FAILURE.code
        )
        update_obj = SmsLogDO(
            id=req.id,
            receive_status=receive_status,
            receive_time=req.receive_time,
            api_receive_code=req.api_receive_code,
            api_receive_msg=req.api_receive_msg,
        )
        await self.sms_log_mapper.update_by_id(update_obj)

    @override
    async def get_sms_log_page(self, page_req_vo: SmsLogPageReqVO) -> PageResult[SmsLogDO]:
        return await self.sms_log_mapper.select_page(page_req_vo)
