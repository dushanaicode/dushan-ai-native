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
from module_system.controller.admin.mail.vo.log.log_page_req_vo import MailLogPageReqVO
from module_system.dal.dataobject.mail.mail_log_do import MailLogDO
from module_system.dal.mapper.mail.mail_log_mapper import MailLogMapper
from module_system.definitions.enums.mail.mail_send_status_enum import MailSendStatusEnum
from module_system.service.mail.bo.mail_batch_log_create_bo import MailBatchLogCreateBO
from module_system.service.mail.bo.mail_log_create_bo import MailLogCreateBO
from module_system.service.mail.bo.mail_send_result_bo import MailSendResultBO
from module_system.service.mail.mail_log_service import MailLogService


@service(interface=MailLogService)
class MailLogServiceImpl(MailLogService):
    """邮件日志服务实现类"""

    mail_log_mapper: MailLogMapper = Inject()
    date_utils: DateUtils = Inject()

    @override
    async def get_mail_log_page(self, req: MailLogPageReqVO) -> PageResult[MailLogDO]:
        return await self.mail_log_mapper.select_page(req)

    @override
    async def get_mail_log(self, mail_log_id: int) -> MailLogDO | None:
        return await self.mail_log_mapper.select_by_id(mail_log_id)

    @override
    @transactional
    async def create_mail_log(self, req: MailLogCreateBO) -> int:
        send_status = (
            MailSendStatusEnum.INIT.code if req.is_send else MailSendStatusEnum.IGNORE.code
        )
        mail_log = MailLogDO()
        mail_log.user_id = req.user_id
        mail_log.user_type = req.user_type
        mail_log.to_mail = req.to_mail
        mail_log.account_id = req.account.id
        mail_log.from_mail = req.account.mail
        mail_log.template_id = req.template.id
        mail_log.template_code = req.template.code
        mail_log.template_nickname = req.template.nickname
        mail_log.template_title = req.template.title
        mail_log.template_content = req.template_content
        mail_log.template_params = req.template_params
        mail_log.send_status = send_status
        await self.mail_log_mapper.insert(mail_log)
        return mail_log.id

    @override
    @transactional
    async def update_mail_send_result(self, req: MailSendResultBO) -> None:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if req.exception is None:
            update_obj = MailLogDO(
                id=req.log_id,
                send_time=now,
                send_status=MailSendStatusEnum.SUCCESS.code,
                send_message_id=req.message_id,
            )
        else:
            update_obj = MailLogDO(
                id=req.log_id,
                send_time=now,
                send_status=MailSendStatusEnum.FAILURE.code,
                send_exception=str(req.exception),
            )
        await self.mail_log_mapper.update_by_id(update_obj)

    @override
    @transactional
    async def create_multiple_mail_log(self, req: MailBatchLogCreateBO) -> int:
        send_status = (
            MailSendStatusEnum.INIT.code if req.is_send else MailSendStatusEnum.IGNORE.code
        )
        mail_log = MailLogDO()
        mail_log.user_id = req.user_id
        mail_log.user_type = req.user_type
        mail_log.to_mail = ",".join(req.to_mails) if req.to_mails else ""
        mail_log.cc_mail = ",".join(req.cc_mails) if req.cc_mails else ""
        mail_log.bcc_mail = ",".join(req.bcc_mails) if req.bcc_mails else ""
        mail_log.account_id = req.account.id
        mail_log.from_mail = req.account.mail
        mail_log.template_id = req.template.id
        mail_log.template_code = req.template.code
        mail_log.template_nickname = req.template.nickname
        mail_log.template_title = req.template.title
        mail_log.template_content = req.template_content
        mail_log.template_params = req.template_params
        mail_log.send_status = send_status
        await self.mail_log_mapper.insert(mail_log)
        return mail_log.id
