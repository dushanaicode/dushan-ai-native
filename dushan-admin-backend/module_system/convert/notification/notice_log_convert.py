from module_system.api.user.dto.admin_user_resp_dto import AdminUserRespDTO
from module_system.controller.admin.notification.vo.notice_log.notice_log_detail_resp_vo import (
    NoticeLogDetailRespVO,
)
from module_system.controller.admin.notification.vo.notice_log.notice_log_message_vo import (
    NoticeLogMessageVO,
)
from module_system.dal.dataobject.notification.notice_log_do import NoticeLogDO
from module_system.dal.dataobject.notification.notice_message_do import NoticeMessageDO


class NoticeLogConvert:
    """通知日志转换器"""

    @staticmethod
    def convert_detail(
        notice_log: NoticeLogDO,
        messages: list[NoticeMessageDO],
        user_map: dict[int, AdminUserRespDTO],
    ) -> NoticeLogDetailRespVO:
        """将 NoticeLogDO + 消息列表 + 用户映射 组装为 NoticeLogDetailRespVO"""
        detail = NoticeLogDetailRespVO.model_validate(notice_log)
        detail.messages = [
            NoticeLogConvert._convert_message(msg, user_map.get(msg.user_id)) for msg in messages
        ]
        return detail

    @staticmethod
    def _convert_message(msg: NoticeMessageDO, user: AdminUserRespDTO | None) -> NoticeLogMessageVO:
        """将单条 NoticeMessageDO 转换为 NoticeLogMessageVO，并填充用户信息"""
        msg_vo = NoticeLogMessageVO.model_validate(msg)
        if user:
            msg_vo.username = user.username
            msg_vo.nickname = user.nickname
        return msg_vo
