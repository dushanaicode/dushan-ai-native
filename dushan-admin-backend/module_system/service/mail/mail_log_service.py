from __future__ import annotations

from typing import Protocol, runtime_checkable

from framework.common.page import PageResult
from module_system.controller.admin.mail.vo.log.mail_log_page_req_vo import MailLogPageReqVO
from module_system.dal.dataobject.mail.mail_log_do import MailLogDO
from module_system.service.mail.bo.mail_batch_log_create_bo import MailBatchLogCreateBO
from module_system.service.mail.bo.mail_log_create_bo import MailLogCreateBO


@runtime_checkable
class MailLogService(Protocol):
    async def get_mail_log_page(self, req: MailLogPageReqVO) -> PageResult[MailLogDO]: ...

    async def get_mail_log(self, mail_log_id: int) -> MailLogDO | None: ...

    async def create_mail_log(self, req: MailLogCreateBO) -> int: ...

    async def create_multiple_mail_log(self, req: MailBatchLogCreateBO) -> int: ...
