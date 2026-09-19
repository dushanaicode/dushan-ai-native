from loguru import logger

from framework.starter_di.public import (
    Inject,
    service,
)
from module_system.dal.dataobject.notification.notice_do import NoticeDO
from module_system.definitions.enums.notification.notification_channel_enum import (
    NotificationChannelEnum,
)
from module_system.framework.notification.channel.notification_channel_handler import (
    NotificationChannelHandler,
)
from module_system.framework.notification.model.notification_channel_result import (
    NotificationChannelResult,
)
from module_system.framework.notification.model.notification_dispatch_context import (
    NotificationDispatchContext,
)
from module_system.framework.notification.model.notification_recipient import NotificationRecipient
from module_system.service.mail.bo.mail_batch_send_bo import MailBatchSendBO
from module_system.service.mail.mail_send_service import MailSendService


@service(providers=[NotificationChannelHandler])
class MailNotificationHandler(NotificationChannelHandler):
    """
    邮件渠道处理器（MQ 异步版）

    通过 MailSendService.send_multiple_mail_to_admin() 发送邮件通知。
    MailSendService 内部完整链路：
        模板校验 → 参数构建 → 日志记录 → MailProducer 投递 MQ → MailSendConsumer 消费 → 实际发送

    需要在系统中配置邮件模板 code = 'system-notice-mail'（在 system_mail_template 表中注册）。
    收集所有用户邮箱后一次性投递到 MQ，由 Consumer 异步批量发送，不会阻塞主线程。
    """

    NOTICE_MAIL_TEMPLATE_CODE = "system-notice-mail"
    mail_send_service: MailSendService = Inject()

    @property
    def channel_type(self) -> NotificationChannelEnum:
        """返回当前通知处理器支持的渠道类型。"""
        return NotificationChannelEnum.MAIL

    async def send(
        self,
        notice: NoticeDO,
        users: list[NotificationRecipient],
        notice_message_id_by_user_id: dict[int, int] | None = None,
        dispatch_context: NotificationDispatchContext | None = None,
    ) -> NotificationChannelResult:
        """批量发送邮件通知"""
        logger.debug(
            "【邮件处理器】开始处理 {} 位用户的邮件通知, 通知ID: {}", len(users), notice.id
        )
        to_mails, mail_user_ids, skipped_user_ids = self._collect_mail_recipients(users)
        if not to_mails:
            logger.warning("【邮件处理器】通知(ID={})无有效收件人，跳过发送", notice.id)
            return NotificationChannelResult.skipped(
                self.channel_type.code, [user.id for user in users], "无有效邮箱地址"
            )
        first_mail_user_id = next((user.id for user in users if user.email))
        command = dict(
            to_mails=to_mails,
            cc_mails=None,
            bcc_mails=None,
            user_id=first_mail_user_id,
            template_code=self.NOTICE_MAIL_TEMPLATE_CODE,
            template_params={"title": notice.title, "content": notice.content},
        )
        return await self._enqueue_mail_notice(notice, command, mail_user_ids, skipped_user_ids)

    @staticmethod
    def _collect_mail_recipients(
        users: list[NotificationRecipient],
    ) -> tuple[list[str], set[int], set[int]]:
        """收集可接收邮件通知的用户邮箱。"""
        to_mails: list[str] = []
        mail_user_ids: set[int] = set()
        skipped_user_ids: set[int] = set()
        for user in users:
            if user.email:
                to_mails.append(user.email)
                mail_user_ids.add(user.id)
                continue
            skipped_user_ids.add(user.id)
            logger.debug("【邮件处理器】用户(ID={})无邮箱地址，跳过", user.id)
        return (to_mails, mail_user_ids, skipped_user_ids)

    async def _enqueue_mail_notice(
        self, notice: NoticeDO, command: dict, mail_user_ids: set[int], skipped_user_ids: set[int]
    ) -> NotificationChannelResult:
        """将邮件通知写入异步发送队列。"""
        try:
            await self.mail_send_service.send_multiple_mail_to_admin(MailBatchSendBO(**command))
            logger.info(
                "【邮件处理器】邮件消息投递成功, 通知ID: {}, 收件人: {}, 跳过(无邮箱): {}",
                notice.id,
                len(command["to_mails"]),
                len(skipped_user_ids),
            )
            return NotificationChannelResult(
                channel_code=self.channel_type.code,
                success_user_ids=mail_user_ids,
                skipped_user_ids=skipped_user_ids,
                failure_reasons=["用户邮箱为空"] if skipped_user_ids else [],
            )
        except Exception as e:
            logger.error(
                "【邮件处理器】邮件消息投递失败, 通知ID: {}, 收件人: {}, 错误: {}",
                notice.id,
                len(command["to_mails"]),
                e,
            )
            return NotificationChannelResult(
                channel_code=self.channel_type.code,
                failed_user_ids=mail_user_ids,
                skipped_user_ids=skipped_user_ids,
                failure_reasons=["邮件 MQ 投递失败"],
            )
