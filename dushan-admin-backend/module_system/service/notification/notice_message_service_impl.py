from __future__ import annotations

from typing import Collection, override

from framework.common.page.schemas.page_result import PageResult
from framework.starter_database.decorators.transactional import transactional
from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.inject import Inject
from module_system.controller.admin.notification.vo.notice_message.notice_message_my_page_req_vo import (
    NoticeMessageMyPageReqVO,
)
from module_system.controller.admin.notification.vo.notice_message.notice_message_page_req_vo import (
    NoticeMessagePageReqVO,
)
from module_system.dal.dataobject.notification.notice_message_do import NoticeMessageDO
from module_system.dal.mapper.notification.notice_message_mapper import (
    NoticeMessageMapper,
)
from module_system.service.notification.bo.notice_message_create_bo import NoticeMessageCreateBO
from module_system.service.notification.notice_message_service import (
    NoticeMessageService,
)


@service(interface=NoticeMessageService)
class NoticeMessageServiceImpl(NoticeMessageService):
    """站内信服务实现类"""

    notice_message_mapper: NoticeMessageMapper = Inject()

    @override
    @transactional
    async def create_notice_message(self, req: NoticeMessageCreateBO) -> int:
        message = NoticeMessageDO(
            user_id=req.user_id,
            user_type=req.user_type,
            notice_id=req.notice.id,
            notice_log_id=req.notice_log_id,
            publisher_info=None
            if req.publisher_info is None
            else req.publisher_info.to_storage_dict(),
            notice_title=req.notice.title,
            notice_content=req.notice.content,
            notice_type=req.notice.type,
            sent_channels=req.sent_channels,
            read_status=False,
        )
        await self.notice_message_mapper.insert(message)
        return message.id

    @override
    async def get_notice_message_page(
        self, req_vo: NoticeMessagePageReqVO
    ) -> PageResult[NoticeMessageDO]:
        return await self.notice_message_mapper.select_page(req_vo)

    @override
    async def get_my_notice_message_page(
        self, req_vo: NoticeMessageMyPageReqVO, user_id: int, user_type: int
    ) -> PageResult[NoticeMessageDO]:
        return await self.notice_message_mapper.select_page_my(req_vo, user_id, user_type)

    @override
    async def get_notice_message(self, id: int) -> NoticeMessageDO:
        return await self.notice_message_mapper.select_by_id(id)

    @override
    async def get_unread_notice_message_list(
        self, user_id: int, user_type: int, size: int
    ) -> list[NoticeMessageDO]:
        return await self.notice_message_mapper.select_unread_list_by_user_id_and_user_type(
            user_id, user_type, size
        )

    @override
    async def get_unread_notice_message_count(self, user_id: int, user_type: int) -> int:
        return await self.notice_message_mapper.select_unread_count_by_user_id_and_user_type(
            user_id, user_type
        )

    @override
    @transactional
    async def update_notice_message_read(
        self, ids: Collection[int], user_id: int, user_type: int
    ) -> int:
        return await self.notice_message_mapper.update_list_read(ids, user_id, user_type)

    @override
    @transactional
    async def update_all_notice_message_read(self, user_id: int, user_type: int) -> int:
        return await self.notice_message_mapper.update_list_read_all(user_id, user_type)
