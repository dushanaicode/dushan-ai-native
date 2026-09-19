from __future__ import annotations

from typing import Protocol, runtime_checkable

from framework.common.page import PageResult
from module_system.controller.admin.sms.vo.log.log_page_req_vo import SmsLogPageReqVO
from module_system.dal.dataobject.sms.sms_log_do import SmsLogDO
from module_system.service.sms.bo.sms_log_create_bo import SmsLogCreateBO
from module_system.service.sms.bo.sms_receive_result_bo import SmsReceiveResultBO
from module_system.service.sms.bo.sms_send_result_bo import SmsSendResultBO


@runtime_checkable
class SmsLogService(Protocol):
    async def create_sms_log(self, req: SmsLogCreateBO) -> int: ...

    async def update_sms_send_result(self, req: SmsSendResultBO) -> None: ...

    async def update_sms_receive_result(self, req: SmsReceiveResultBO) -> None: ...

    async def get_sms_log_page(self, page_req_vo: SmsLogPageReqVO) -> PageResult[SmsLogDO]: ...
