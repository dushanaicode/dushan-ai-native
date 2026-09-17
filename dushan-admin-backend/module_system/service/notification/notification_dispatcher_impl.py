from loguru import logger

from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.inject import Inject
from module_system.dal.dataobject.notification.notice_do import NoticeDO
from module_system.framework.notification.channel.notification_channel_handler import (
    NotificationChannelHandler,
)
from module_system.framework.notification.model.notice_publisher_info_dto import (
    NoticePublisherInfoDTO,
)
from module_system.framework.notification.model.notification_channel_result import (
    NotificationChannelResult,
)
from module_system.framework.notification.model.notification_dispatch_context import (
    NotificationDispatchContext,
)
from module_system.framework.notification.model.notification_recipient import NotificationRecipient
from module_system.service.notification.bo.notice_log_result_bo import NoticeLogResultBO
from module_system.service.notification.bo.notice_message_create_bo import NoticeMessageCreateBO
from module_system.service.notification.notice_log_service import (
    NoticeLogService,
)
from module_system.service.notification.notice_message_service import (
    NoticeMessageService,
)
from module_system.service.notification.notification_dispatcher import (
    NotificationDispatcher,
)


@service(interface=NotificationDispatcher)
class NotificationDispatcherImpl(NotificationDispatcher):
    """
    通知处理器编排器实现（MQ 异步版）

    负责：
    1. 为所有用户创建站内信记录（notice_message），并关联 notice_log_id
    2. 根据通知的渠道列表，调度对应的处理器进行分发
       - INTERNAL：WebSocket 实时推送（站内信）
       - SMS：通过 SmsSendService → SmsProducer → MQ 异步发送短信
       - MAIL：通过 MailSendService → MailProducer → MQ 异步发送邮件
    3. 更新推送日志的成功/失败计数及最终状态
    """

    notice_message_service: NoticeMessageService = Inject()
    notice_log_service: NoticeLogService = Inject()
    notification_channel_handlers: list[NotificationChannelHandler] = Inject()

    async def send_notification(
        self,
        notice: NoticeDO,
        users: list[NotificationRecipient],
        dispatch_context: NotificationDispatchContext | None = None,
    ) -> set[int]:
        """根据通知中定义的渠道，调度对应的处理器进行分发"""
        if not users:
            return set()
        context = dispatch_context or NotificationDispatchContext()
        user_ids = {user.id for user in users}
        failed_user_ids: set[int] = set()
        notice_message_id_by_user_id = {}
        try:
            notice_message_id_by_user_id, failed_user_ids = await self._create_notice_messages(
                notice, users, context.notice_log_id, context.publisher_info
            )
            dispatch_users = [user for user in users if user.id in notice_message_id_by_user_id]
            channel_results = await self._dispatch_channels(
                notice, dispatch_users, notice_message_id_by_user_id, context
            )
            failed_user_ids.update(self._collect_failed_user_ids(channel_results))
        except Exception as e:
            logger.error(
                "【通知编排器】推送过程发生未预期异常, 通知ID: {}, 日志ID: {}, 原因: {}",
                notice.id,
                context.notice_log_id,
                e,
            )
            failed_user_ids = user_ids
        finally:
            await self._update_notice_log_result(context.notice_log_id, user_ids, failed_user_ids)
        return failed_user_ids

    async def _create_notice_messages(
        self,
        notice: NoticeDO,
        users: list[NotificationRecipient],
        notice_log_id: int | None,
        publisher_info: NoticePublisherInfoDTO | None,
    ) -> tuple[dict[int, int], set[int]]:
        """为目标用户批量创建站内信消息记录。"""
        logger.debug(
            "【通知编排器】开始为 {} 位用户创建通知记录, 通知ID: {}, 通知日志ID: {}",
            len(users),
            notice.id,
            notice_log_id,
        )
        notice_message_id_by_user_id: dict[int, int] = {}
        failed_user_ids: set[int] = set()
        for user in users:
            try:
                notice_message_id_by_user_id[
                    user.id
                ] = await self.notice_message_service.create_notice_message(
                    NoticeMessageCreateBO(
                        publisher_info=publisher_info,
                        user_id=user.id,
                        user_type=notice.user_type,
                        notice=notice,
                        sent_channels=notice.channels,
                        notice_log_id=notice_log_id,
                    )
                )
            except Exception as e:
                failed_user_ids.add(user.id)
                logger.error("【通知编排器】为用户 {} 创建通知记录失败: {}", user.id, e)
        return (notice_message_id_by_user_id, failed_user_ids)

    async def _dispatch_channels(
        self,
        notice: NoticeDO,
        users: list[NotificationRecipient],
        notice_message_id_by_user_id: dict[int, int],
        dispatch_context: NotificationDispatchContext,
    ) -> list[NotificationChannelResult]:
        """按通知渠道调度对应处理器。"""
        results: list[NotificationChannelResult] = []
        handlers = self._get_handlers()
        for channel_code in notice.channels:
            handler = handlers.get(channel_code)
            if handler is None:
                logger.warning(
                    "【通知编排器】未找到渠道 '{}' 对应的处理器，标记为失败", channel_code
                )
                results.append(
                    NotificationChannelResult.failed(
                        channel_code, [user.id for user in users], "渠道处理器未注册"
                    )
                )
                continue
            results.append(
                await self._send_channel(
                    handler, notice, users, notice_message_id_by_user_id, dispatch_context
                )
            )
        return results

    async def _send_channel(
        self,
        handler: NotificationChannelHandler,
        notice: NoticeDO,
        users: list[NotificationRecipient],
        notice_message_id_by_user_id: dict[int, int],
        dispatch_context: NotificationDispatchContext,
    ) -> NotificationChannelResult:
        """执行单个通知渠道处理器并包装失败结果。"""
        try:
            return await handler.send(notice, users, notice_message_id_by_user_id, dispatch_context)
        except Exception as e:
            logger.error("【通知编排器】执行渠道 '{}' 处理器失败: {}", handler.channel_type.code, e)
            return NotificationChannelResult.failed(
                handler.channel_type.code, [user.id for user in users], "渠道处理器执行异常"
            )

    def _get_handlers(self) -> dict[str, NotificationChannelHandler]:
        """返回通知渠道与处理器的映射关系。"""
        return {
            handler.channel_type.code: handler for handler in self.notification_channel_handlers
        }

    @staticmethod
    def _collect_failed_user_ids(channel_results: list[NotificationChannelResult]) -> set[int]:
        """汇总各渠道发送失败的用户编号。"""
        failed_user_ids: set[int] = set()
        for result in channel_results:
            failed_user_ids.update(result.unsuccessful_user_ids)
        return failed_user_ids

    async def _update_notice_log_result(
        self, notice_log_id: int | None, user_ids: set[int], failed_user_ids: set[int]
    ) -> None:
        """回写通知日志的成功和失败统计。"""
        if notice_log_id is None:
            return
        try:
            effective_failed_user_ids = failed_user_ids & user_ids
            success_count = len(user_ids - effective_failed_user_ids)
            await self.notice_log_service.update_notice_log_result(
                NoticeLogResultBO(
                    notice_log_id=notice_log_id,
                    success_count=success_count,
                    fail_count=len(effective_failed_user_ids),
                )
            )
        except Exception:
            logger.error("通知日志结果写入失败: {}", notice_log_id)
            raise
