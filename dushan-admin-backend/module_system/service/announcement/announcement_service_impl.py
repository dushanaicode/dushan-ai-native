from __future__ import annotations

from datetime import datetime, timezone
from typing import override

from framework.common.enums import StatusEnum
from framework.common.exception import ServiceException
from framework.common.page import PageResult
from framework.starter_database.public import (
    transactional,
)
from framework.starter_di.public import (
    Inject,
    service,
)
from framework.starter_security.public import (
    SecurityContext,
)
from module_system.api.notification.dto.notice_send_dto import NoticeSendDTO
from module_system.controller.admin.announcement.vo.announcement_page_req_vo import (
    AnnouncementPageReqVO,
)
from module_system.controller.admin.announcement.vo.announcement_save_req_vo import (
    AnnouncementSaveReqVO,
)
from module_system.dal.dataobject.announcement.announcement_do import AnnouncementDO
from module_system.dal.mapper.announcement.announcement_mapper import (
    AnnouncementMapper,
)
from module_system.definitions.constants.error_code_constants import ErrorCodeConstants
from module_system.definitions.enums.announcement.announcement_status_enum import (
    AnnouncementStatusEnum,
)
from module_system.definitions.enums.notification.notification_channel_enum import (
    NotificationChannelEnum,
)
from module_system.service.announcement.announcement_service import (
    AnnouncementService,
)
from module_system.service.notification.notice_service import NoticeService
from module_system.service.user.admin_user_service import AdminUserService


@service(interface=AnnouncementService)
class AnnouncementServiceImpl(AnnouncementService):
    """管理公告内容、发布与过期状态。"""

    security: SecurityContext = Inject()
    announcement_mapper: AnnouncementMapper = Inject()
    notice_service: NoticeService = Inject()
    admin_user_service: AdminUserService = Inject()

    @override
    @transactional
    async def create_announcement(self, req_vo: AnnouncementSaveReqVO) -> int:
        announcement = AnnouncementDO(**req_vo.model_dump(by_alias=False))
        await self.announcement_mapper.insert(announcement)
        return announcement.id

    @override
    @transactional
    async def update_announcement(self, req_vo: AnnouncementSaveReqVO) -> bool:
        await self._validate_exists(req_vo.id)
        update_obj = AnnouncementDO(**req_vo.model_dump(by_alias=False))
        await self.announcement_mapper.update_by_id(update_obj)
        return True

    @override
    @transactional
    async def delete_announcement(self, id: int) -> bool:
        await self._validate_exists(id)
        await self.announcement_mapper.delete_by_id(id)
        return True

    @override
    @transactional
    async def delete_announcement_batch(self, ids: list[int]) -> int:
        if not ids:
            return 0
        return await self.announcement_mapper.delete_by_ids(ids)

    @override
    async def get_announcement(self, id: int) -> AnnouncementDO:
        return await self._validate_exists(id)

    @override
    async def get_announcement_page(
        self, page_req_vo: AnnouncementPageReqVO
    ) -> PageResult[AnnouncementDO]:
        return await self.announcement_mapper.select_page(page_req_vo)

    @override
    async def expire_announcements(self, current_time: datetime) -> int:
        return await self.announcement_mapper.expire_published(current_time)

    @override
    @transactional
    async def schedule_announcement_publish(self, id: int) -> bool:
        announcement = await self._validate_exists(id)
        if announcement.status != AnnouncementStatusEnum.DRAFT.code:
            raise ServiceException(
                ErrorCodeConstants.ANNOUNCEMENT_STATUS_ERROR,
                msg="只有草稿状态的公告才能设置定时发布",
            )
        if not announcement.publish_time:
            raise ServiceException(ErrorCodeConstants.ANNOUNCEMENT_PUBLISH_TIME_REQUIRED)
        current_time = datetime.now(timezone.utc).replace(tzinfo=None)
        publish_time = announcement.publish_time
        if publish_time <= current_time:
            raise ServiceException(ErrorCodeConstants.ANNOUNCEMENT_PUBLISH_TIME_INVALID)
        announcement.status = AnnouncementStatusEnum.WAIT_PUBLISH.code
        await self.announcement_mapper.update_by_id(announcement)
        return True

    @override
    async def get_wait_publish_announcements(self) -> list[AnnouncementDO]:
        return await self.announcement_mapper.select_list_by_status(
            AnnouncementStatusEnum.WAIT_PUBLISH.code
        )

    @override
    @transactional
    async def publish_announcement(self, id: int) -> bool:
        """手动和定时发布共用同一事务；重复发布不重复生成站内信。"""
        announcement = await self.announcement_mapper.select_for_update(id)
        if announcement is None:
            raise ServiceException(ErrorCodeConstants.ANNOUNCEMENT_NOT_FOUND)
        if announcement.status == AnnouncementStatusEnum.PUBLISHED.code:
            return False
        if announcement.status not in (
            AnnouncementStatusEnum.DRAFT.code,
            AnnouncementStatusEnum.WAIT_PUBLISH.code,
        ):
            raise ServiceException(
                ErrorCodeConstants.ANNOUNCEMENT_STATUS_ERROR,
                msg="只有草稿或待发布状态的公告才能发布",
            )
        announcement.status = AnnouncementStatusEnum.PUBLISHED.code
        announcement.publish_time = datetime.now(timezone.utc).replace(tzinfo=None)
        await self.announcement_mapper.update_by_id(announcement)
        await self._publish_announcement_notice(announcement)
        return True

    async def _publish_announcement_notice(self, announcement: AnnouncementDO) -> None:
        """为启用的后台用户创建公告站内信。"""
        users = await self.admin_user_service.get_user_list_by_status(StatusEnum.ENABLE.code)
        user_ids = [user.id for user in users]
        if not user_ids:
            raise ServiceException(ErrorCodeConstants.NOTICE_SEND_USER_NOT_EXISTS)
        identity = self.security.current()
        publisher_info = (
            None
            if identity is None
            else {"id": int(identity.account_id), "nickname": None, "avatar": None}
        )
        await self.notice_service.send_notice_direct(
            NoticeSendDTO(
                title=announcement.title,
                content=announcement.content,
                user_ids=user_ids,
                channels=[NotificationChannelEnum.INTERNAL.code],
                publisher_info=publisher_info,
                notice_code="system_announcement_publish",
            )
        )

    async def _validate_exists(self, id: int) -> AnnouncementDO:
        """校验公告是否存在"""
        announcement = await self.announcement_mapper.select_by_id(id)
        if not announcement:
            raise ServiceException(ErrorCodeConstants.ANNOUNCEMENT_NOT_FOUND)
        return announcement
