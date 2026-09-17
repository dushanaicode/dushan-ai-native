from framework.common.schemas.base_bo import BaseBO
from module_system.dal.dataobject.notification.notice_do import NoticeDO
from module_system.framework.notification.model.notice_publisher_info_dto import (
    NoticePublisherInfoDTO,
)


class NoticeMessageCreateBO(BaseBO):
    user_id: int
    user_type: int
    notice: NoticeDO
    sent_channels: list[str]
    publisher_info: NoticePublisherInfoDTO | None
    notice_log_id: int | None = None
