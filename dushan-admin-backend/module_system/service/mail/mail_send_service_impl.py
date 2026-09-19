from __future__ import annotations

from typing import Any, override
from uuid import uuid4

from framework.common.enums import StatusEnum, UserTypeEnum
from framework.common.exception import ServiceException
from framework.starter_database.public import (
    transactional,
)
from framework.starter_di.public import (
    Inject,
    service,
)
from framework.starter_mq.public import (
    MessageResultUnknown,
)
from module_system.dal.dataobject.mail.mail_account_do import MailAccountDO
from module_system.dal.dataobject.mail.mail_template_do import MailTemplateDO
from module_system.dal.dataobject.user.admin_user_do import AdminUserDO
from module_system.definitions.constants.error_code_constants import ErrorCodeConstants
from module_system.framework.mail.client.smtp_mail_client import SmtpMailClient
from module_system.framework.mail.model.mail_account import MailAccount
from module_system.framework.notification.delivery.delivery_cancelled import DeliveryCancelled
from module_system.framework.notification.delivery.delivery_definite_failure import (
    DeliveryDefiniteFailure,
)
from module_system.mq.message.mail.mail_send_message import MailSendMessage
from module_system.mq.producer.mail.mail_producer_protocol import MailProducerProtocol
from module_system.service.mail.bo.mail_batch_dispatch_bo import MailBatchDispatchBO
from module_system.service.mail.bo.mail_batch_log_create_bo import MailBatchLogCreateBO
from module_system.service.mail.bo.mail_batch_send_bo import MailBatchSendBO
from module_system.service.mail.bo.mail_dispatch_bo import MailDispatchBO
from module_system.service.mail.bo.mail_log_create_bo import MailLogCreateBO
from module_system.service.mail.bo.mail_send_bo import MailSendBO
from module_system.service.mail.bo.mail_send_result_bo import MailSendResultBO
from module_system.service.mail.mail_account_service import MailAccountService
from module_system.service.mail.mail_log_service import MailLogService
from module_system.service.mail.mail_send_service import MailSendService
from module_system.service.mail.mail_template_service import MailTemplateService
from module_system.service.member.member_service import MemberService
from module_system.service.notification.notification_delivery_service import (
    NotificationDeliveryService,
)
from module_system.service.user.admin_user_service import AdminUserService


@service(interface=MailSendService)
class MailSendServiceImpl(MailSendService):
    """邮件发送服务实现类"""

    admin_user_service: AdminUserService = Inject()
    member_service: MemberService = Inject()
    mail_account_service: MailAccountService = Inject()
    mail_template_service: MailTemplateService = Inject()
    mail_log_service: MailLogService = Inject()
    mail_producer: MailProducerProtocol = Inject()

    @override
    async def send_single_mail_to_admin(self, req: MailSendBO) -> int:
        mail = req.mail
        if not mail:
            user: AdminUserDO = await self.admin_user_service.get_user(req.user_id)
            if user is not None:
                mail = user.email
        return await self.send_single_mail(
            MailDispatchBO(
                mail=mail,
                user_id=req.user_id,
                user_type=UserTypeEnum.ADMIN.code,
                template_code=req.template_code,
                template_params=req.template_params,
            )
        )

    @override
    async def send_single_mail_to_member(self, req: MailSendBO) -> int:
        mail = req.mail
        if not mail and self.member_service:
            mail = await self.member_service.get_member_user_email(req.user_id)
        return await self.send_single_mail(
            MailDispatchBO(
                mail=mail,
                user_id=req.user_id,
                user_type=UserTypeEnum.MEMBER.code,
                template_code=req.template_code,
                template_params=req.template_params,
            )
        )

    @override
    async def send_multiple_mail_to_admin(self, req: MailBatchSendBO) -> int:
        to_mails = req.to_mails
        if not to_mails:
            user: AdminUserDO = await self.admin_user_service.get_user(req.user_id)
            if user is not None and user.email:
                to_mails = [user.email]
        return await self.send_multiple_mail(
            MailBatchDispatchBO(
                to_mails=to_mails,
                cc_mails=req.cc_mails,
                bcc_mails=req.bcc_mails,
                user_id=req.user_id,
                user_type=UserTypeEnum.ADMIN.code,
                template_code=req.template_code,
                template_params=req.template_params,
            )
        )

    @override
    async def send_multiple_mail_to_member(self, req: MailBatchSendBO) -> int:
        to_mails = req.to_mails
        if not to_mails and self.member_service:
            member_email = await self.member_service.get_member_user_email(req.user_id)
            if member_email:
                to_mails = [member_email]
        return await self.send_multiple_mail(
            MailBatchDispatchBO(
                to_mails=to_mails,
                cc_mails=req.cc_mails,
                bcc_mails=req.bcc_mails,
                user_id=req.user_id,
                user_type=UserTypeEnum.MEMBER.code,
                template_code=req.template_code,
                template_params=req.template_params,
            )
        )

    @transactional
    @override
    async def send_single_mail(self, req: MailDispatchBO) -> int:
        template = await self._validate_template(req.template_code)
        account = await self._validate_account(template.account_id)
        self._validate_mail(req.mail)
        self._validate_template_params(template, req.template_params)
        is_send = template.status == StatusEnum.ENABLE.code
        title = self.mail_template_service.format_mail_template_content(
            template.title, req.template_params
        )
        content = self.mail_template_service.format_mail_template_content(
            template.content, req.template_params
        )
        send_log_id = await self.mail_log_service.create_mail_log(
            MailLogCreateBO(
                user_id=req.user_id,
                user_type=req.user_type,
                to_mail=req.mail,
                account=account,
                template=template,
                template_content=content,
                template_params=req.template_params,
                is_send=is_send,
            )
        )
        if is_send:
            try:
                message_id = uuid4().hex
                await self.mail_producer.send_mail_message(
                    MailSendMessage(
                        message_id=message_id,
                        log_id=send_log_id,
                        to_mails=[req.mail],
                        account_id=account.id,
                        nickname=template.nickname,
                        title=title,
                        content=content,
                    )
                )
            except Exception as e:
                await self.mail_log_service.update_mail_send_result(
                    MailSendResultBO(log_id=send_log_id, message_id=None, exception=e)
                )
                raise
        return send_log_id

    @transactional
    @override
    async def send_multiple_mail(self, req: MailBatchDispatchBO) -> int:
        template = await self._validate_template(req.template_code)
        account = await self._validate_account(template.account_id)
        if not req.to_mails:
            raise ServiceException(ErrorCodeConstants.MAIL_SEND_MAIL_NOT_EXISTS)
        for mail in req.to_mails:
            self._validate_mail(mail)
        if req.cc_mails:
            for mail in req.cc_mails:
                self._validate_mail(mail)
        if req.bcc_mails:
            for mail in req.bcc_mails:
                self._validate_mail(mail)
        self._validate_template_params(template, req.template_params)
        is_send = template.status == StatusEnum.ENABLE.code
        title = self.mail_template_service.format_mail_template_content(
            template.title, req.template_params
        )
        content = self.mail_template_service.format_mail_template_content(
            template.content, req.template_params
        )
        send_log_id = await self.mail_log_service.create_multiple_mail_log(
            MailBatchLogCreateBO(
                user_id=req.user_id,
                user_type=req.user_type,
                to_mails=req.to_mails,
                cc_mails=req.cc_mails,
                bcc_mails=req.bcc_mails,
                account=account,
                template=template,
                template_content=content,
                template_params=req.template_params,
                is_send=is_send,
            )
        )
        if is_send:
            try:
                message_id = uuid4().hex
                await self.mail_producer.send_mail_message(
                    MailSendMessage(
                        message_id=message_id,
                        log_id=send_log_id,
                        to_mails=req.to_mails,
                        cc_mails=req.cc_mails,
                        bcc_mails=req.bcc_mails,
                        account_id=account.id,
                        nickname=template.nickname,
                        title=title,
                        content=content,
                    )
                )
            except Exception as e:
                await self.mail_log_service.update_mail_send_result(
                    MailSendResultBO(log_id=send_log_id, message_id=None, exception=e)
                )
                raise
        return send_log_id

    async def _validate_template(self, template_code: str) -> MailTemplateDO:
        """校验邮件模板是否存在"""
        template = await self.mail_template_service.get_mail_template_by_code(template_code)
        if template is None:
            raise ServiceException(ErrorCodeConstants.MAIL_TEMPLATE_NOT_EXISTS)
        return template

    async def _validate_account(self, account_id: int) -> MailAccountDO:
        """校验邮箱账号是否存在"""
        account = await self.mail_account_service.get_mail_account(account_id)
        if account is None:
            raise ServiceException(ErrorCodeConstants.MAIL_ACCOUNT_NOT_EXISTS)
        return account

    @staticmethod
    def _validate_mail(mail: str) -> None:
        """校验邮箱地址是否为空"""
        if not mail:
            raise ServiceException(ErrorCodeConstants.MAIL_SEND_MAIL_NOT_EXISTS)

    @staticmethod
    def _validate_template_params(
        template: MailTemplateDO, template_params: dict[str, Any]
    ) -> None:
        """校验模板参数是否完整"""
        for key in template.params:
            if template_params.get(key) is None:
                raise ServiceException(ErrorCodeConstants.MAIL_SEND_TEMPLATE_PARAM_MISS, key)

    @staticmethod
    def _build_mail_account(account: Any, nickname: str | None) -> MailAccount:
        """构建 MailAccount 实例"""
        from_address = (
            f"{nickname} <{account.mail}>" if nickname and nickname.strip() else account.mail
        )
        return MailAccount(
            from_address=from_address,
            auth=True,
            user=account.username,
            password=account.password,
            host=account.host,
            port=account.port,
            ssl_enable=account.ssl_enable,
            starttls_enable=account.starttls_enable,
        )

    delivery: NotificationDeliveryService = Inject()

    async def do_send_mail(self, message: MailSendMessage) -> None:
        account = await self._validate_account(message.account_id)
        attempt = await self.delivery.claim("mail", message.log_id)
        if attempt is None:
            return
        try:
            identifier = await SmtpMailClient.send_multiple(
                self._build_mail_account(account, message.nickname),
                message.to_mails,
                message.cc_mails,
                message.bcc_mails,
                message.title,
                message.content,
                True,
                on_request_started=lambda: self.delivery.started("mail", message.log_id, attempt),
            )
        except DeliveryCancelled:
            await self.delivery.finish("mail", message.log_id, attempt, send_status=40)
            return
        except DeliveryDefiniteFailure as error:
            await self.delivery.finish(
                "mail", message.log_id, attempt, send_status=20, send_exception=type(error).__name__
            )
            raise
        except Exception as error:
            await self.delivery.finish(
                "mail", message.log_id, attempt, send_status=5, send_exception=type(error).__name__
            )
            raise MessageResultUnknown("邮件发送结果未知") from error
        await self.delivery.finish(
            "mail", message.log_id, attempt, send_status=10, send_message_id=identifier
        )
