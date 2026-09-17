from __future__ import annotations

from typing import override

from loguru import logger
from sqlalchemy import select

from framework.common.page.schemas.page_result import PageResult
from framework.starter_database.decorators.transactional import transactional
from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.inject import Inject
from module_system.controller.admin.notification.vo.notice_log.notice_log_page_req_vo import (
    NoticeLogPageReqVO,
)
from module_system.dal.dataobject.notification.notice_log_do import NoticeLogDO
from module_system.dal.dataobject.notification.notice_message_do import NoticeMessageDO
from module_system.dal.mapper.notification.notice_log_mapper import (
    NoticeLogMapper,
)
from module_system.dal.mapper.notification.notice_message_mapper import (
    NoticeMessageMapper,
)
from module_system.definitions.enums.notification.notice_push_status_enum import (
    NoticePushStatusEnum,
)
from module_system.service.notification.bo.notice_log_create_bo import NoticeLogCreateBO
from module_system.service.notification.bo.notice_log_result_bo import NoticeLogResultBO
from module_system.service.notification.notice_log_service import (
    NoticeLogService,
)


@service(interface=NoticeLogService)
class NoticeLogServiceImpl(NoticeLogService):
    """通知日志服务实现类"""

    notice_log_mapper: NoticeLogMapper = Inject()
    notice_message_mapper: NoticeMessageMapper = Inject()

    @override
    @transactional
    async def create_notice_log(self, req: NoticeLogCreateBO) -> int:
        notice_log = NoticeLogDO(
            notice_id=req.notice_id,
            notice_title=req.notice_title,
            notice_type=req.notice_type,
            push_target_type=req.push_target_type,
            target_user_ids=req.target_user_ids,
            target_dept_ids=req.target_dept_ids,
            target_dept_names=req.target_dept_names,
            push_channels=req.push_channels,
            total_count=req.total_count,
            success_count=0,
            fail_count=0,
            push_status=NoticePushStatusEnum.PUSHING.code,
            publisher_info=req.publisher_info,
        )
        await self.notice_log_mapper.insert(notice_log)
        logger.debug(
            f"【NoticeLogServiceImpl】创建通知日志, ID: {notice_log.id}, 通知ID: {req.notice_id}, 总人数: {req.total_count}"
        )
        return notice_log.id

    @override
    @transactional
    async def update_notice_log_result(self, req: NoticeLogResultBO) -> None:
        notice_log = await self.notice_log_mapper.select_by_id(req.notice_log_id)
        if notice_log is None:
            logger.warning(f"【NoticeLogServiceImpl】通知日志不存在, ID: {req.notice_log_id}")
            return
        if req.fail_count == 0:
            push_status = NoticePushStatusEnum.ALL_SUCCESS.code
        elif req.success_count == 0:
            push_status = NoticePushStatusEnum.ALL_FAILED.code
        else:
            push_status = NoticePushStatusEnum.PARTIAL_FAIL.code
        notice_log.success_count = req.success_count
        notice_log.fail_count = req.fail_count
        notice_log.push_status = push_status
        await self.notice_log_mapper.update_by_id(notice_log)

    @override
    async def get_notice_log_page(self, req_vo: NoticeLogPageReqVO) -> PageResult[NoticeLogDO]:
        return await self.notice_log_mapper.select_page(req_vo)

    @override
    async def get_notice_log(self, notice_log_id: int) -> NoticeLogDO | None:
        return await self.notice_log_mapper.select_by_id(notice_log_id)

    @override
    async def get_notice_log_messages(self, notice_log_id: int) -> list[NoticeMessageDO]:
        """获取某个推送批次下的所有站内信消息"""
        stmt = (
            select(NoticeMessageDO)
            .where(
                NoticeMessageDO.notice_log_id == notice_log_id, NoticeMessageDO.deleted.is_(False)
            )
            .order_by(NoticeMessageDO.id.asc())
        )
        result = await self.notice_message_mapper.read(stmt)
        return list(result.scalars().all())
