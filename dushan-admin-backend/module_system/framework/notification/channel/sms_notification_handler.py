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
from module_system.service.sms.bo.sms_send_bo import SmsSendBO
from module_system.service.sms.sms_send_service import SmsSendService


@service(providers=[NotificationChannelHandler])
class SmsNotificationHandler(NotificationChannelHandler):
    """
    短信渠道处理器（MQ 异步版）

    通过 SmsSendService.send_single_sms_to_admin() 发送短信通知。
    SmsSendService 内部完整链路：
        模板校验 → 参数构建 → 日志记录 → SmsProducer 投递 MQ → SmsSendConsumer 消费 → 实际发送

    短信模板编码从 notice.sms_template_code 获取（前端选择）。
    大批量用户场景下，每条消息独立投递到 MQ 异步处理，不会阻塞主线程。
    """

    sms_send_service: SmsSendService = Inject()

    @property
    def channel_type(self) -> NotificationChannelEnum:
        """返回当前通知处理器支持的渠道类型。"""
        return NotificationChannelEnum.SMS

    async def send(
        self,
        notice: NoticeDO,
        users: list[NotificationRecipient],
        notice_message_id_by_user_id: dict[int, int] | None = None,
        dispatch_context: NotificationDispatchContext | None = None,
    ) -> NotificationChannelResult:
        """批量发送短信通知"""
        logger.debug(
            "【短信处理器】开始向 {} 位用户投递短信通知到 MQ, 通知ID: {}", len(users), notice.id
        )
        template_code = notice.sms_template_code
        if not template_code:
            logger.warning("【短信处理器】通知(ID={})未配置短信模板编码，跳过发送", notice.id)
            return NotificationChannelResult.skipped(
                self.channel_type.code, [user.id for user in users], "短信模板编码未配置"
            )
        result = await self._send_sms_messages(notice, users, template_code)
        logger.info(
            "【短信处理器】短信消息投递完成, 通知ID: {}, 成功投递: {}, 投递失败: {}, 跳过: {}",
            notice.id,
            result.success_count,
            len(result.failed_user_ids),
            len(result.skipped_user_ids),
        )
        return result

    async def _send_sms_messages(
        self, notice: NoticeDO, users: list[NotificationRecipient], template_code: str
    ) -> NotificationChannelResult:
        """将短信通知写入异步发送队列。"""
        template_params = {"title": notice.title, "content": notice.content}
        success_user_ids: set[int] = set()
        failed_user_ids: set[int] = set()
        skipped_user_ids: set[int] = set()
        for user in users:
            if not user.mobile:
                skipped_user_ids.add(user.id)
                continue
            try:
                await self.sms_send_service.send_single_sms_to_admin(
                    SmsSendBO(
                        mobile=user.mobile,
                        user_id=user.id,
                        template_code=template_code,
                        template_params=template_params,
                    )
                )
                success_user_ids.add(user.id)
            except Exception as e:
                failed_user_ids.add(user.id)
                logger.error("【短信处理器】向用户(ID={})投递短信消息失败: {}", user.id, e)
        return NotificationChannelResult(
            channel_code=self.channel_type.code,
            success_user_ids=success_user_ids,
            failed_user_ids=failed_user_ids,
            skipped_user_ids=skipped_user_ids,
            failure_reasons=["用户手机号为空"] if skipped_user_ids else [],
        )
