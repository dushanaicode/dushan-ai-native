from __future__ import annotations

from typing import override

from loguru import logger

from framework.common.enums.builtin_type_enum import BuiltinTypeEnum
from framework.common.enums.user_type_enum import UserTypeEnum
from framework.common.exception.constants.global_error_code_constants import (
    GlobalErrorCodeConstants,
)
from framework.common.exception.exceptions.service_exception import ServiceException
from framework.common.page.schemas.page_result import PageResult
from framework.starter_database.decorators.transactional import transactional
from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.inject import Inject
from framework.starter_security.context.security_context import SecurityContext
from module_system.api.notification.dto.notice_send_dto import NoticeSendDTO
from module_system.controller.admin.notification.vo.notice.notice_page_req_vo import NoticePageReqVO
from module_system.controller.admin.notification.vo.notice.notice_save_req_vo import NoticeSaveReqVO
from module_system.controller.admin.notification.vo.notice.notice_send_req_vo import NoticeSendReqVO
from module_system.dal.dataobject.notification.notice_do import NoticeDO
from module_system.dal.mapper.notification.notice_mapper import (
    NoticeMapper,
)
from module_system.definitions.constants.error_code_constants import ErrorCodeConstants
from module_system.definitions.enums.notification.notice_push_target_type_enum import (
    NoticePushTargetTypeEnum,
)
from module_system.framework.notification.model.notice_publisher_info_dto import (
    NoticePublisherInfoDTO,
)
from module_system.framework.notification.model.notification_dispatch_context import (
    NotificationDispatchContext,
)
from module_system.service.dept.dept_service import DeptService
from module_system.service.notification.bo.notice_log_create_bo import NoticeLogCreateBO
from module_system.service.notification.notice_log_service import (
    NoticeLogService,
)
from module_system.service.notification.notice_service import NoticeService
from module_system.service.notification.notification_dispatcher import (
    NotificationDispatcher,
)
from module_system.service.user.admin_user_service import AdminUserService


@service(interface=NoticeService)
class NoticeServiceImpl(NoticeService):
    security: SecurityContext = Inject()
    "系统通知服务实现类"
    notice_mapper: NoticeMapper = Inject()
    dept_service: DeptService = Inject()
    admin_user_service: AdminUserService = Inject()
    notification_dispatcher: NotificationDispatcher = Inject()
    notice_log_service: NoticeLogService = Inject()

    @override
    @transactional
    async def create_notice(self, create_req_vo: NoticeSaveReqVO) -> int:
        notice = NoticeDO(**create_req_vo.model_dump(by_alias=False))
        await self.notice_mapper.insert(notice)
        return notice.id

    @override
    @transactional
    async def update_notice(self, update_req_vo: NoticeSaveReqVO) -> None:
        await self._validate_for_update(update_req_vo.id)
        update_obj = NoticeDO(**update_req_vo.model_dump(by_alias=False))
        await self.notice_mapper.update_by_id(update_obj)

    @override
    @transactional
    async def update_status(self, notice_id: int, status: int) -> None:
        """更新系统通知状态"""
        await self._validate_for_update(notice_id)
        update_obj = NoticeDO(id=notice_id, status=status)
        await self.notice_mapper.update_by_id(update_obj)

    @override
    @transactional
    async def delete_notice(self, id: int) -> None:
        await self._validate_for_update(id)
        await self.notice_mapper.delete_by_id(id)

    @override
    @transactional
    async def delete_notice_batch(self, ids: list[int]) -> int:
        notices = await self.notice_mapper.select_by_ids(ids)
        if len(notices) != len(ids):
            raise ServiceException(ErrorCodeConstants.NOTICE_NOT_FOUND)
        for n in notices:
            if n.code:
                raise ServiceException(ErrorCodeConstants.NOTICE_CAN_NOT_UPDATE_SYSTEM_TYPE)
        return await self.notice_mapper.delete_by_ids(ids)

    @override
    async def get_notice_page(self, req_vo: NoticePageReqVO) -> PageResult[NoticeDO]:
        return await self.notice_mapper.select_page(req_vo)

    @override
    async def get_notice(self, id: int) -> NoticeDO:
        return await self.notice_mapper.select_by_id(id)

    @override
    async def send_notice(self, req: NoticeSendReqVO) -> None:
        notice_id, user_ids, dept_ids = req.id, req.user_ids, req.dept_ids
        notice = await self.get_notice(notice_id)
        if notice is None:
            raise ServiceException(ErrorCodeConstants.NOTICE_NOT_FOUND)
        target_user_ids: set[int] = set()
        if user_ids:
            target_user_ids.update(user_ids)
        all_dept_ids: set[int] = set()
        if dept_ids:
            for dept_id in dept_ids:
                child_dept_ids = await self.dept_service.get_child_dept_id_list_from_cache(dept_id)
                all_dept_ids.update(child_dept_ids)
                all_dept_ids.add(dept_id)
            if all_dept_ids:
                dept_users = await self.admin_user_service.get_user_list_by_dept_ids(
                    list(all_dept_ids)
                )
                target_user_ids.update(user.id for user in dept_users)
        if not target_user_ids:
            return
        final_user_ids = list(target_user_ids)
        user_info_list = []
        if notice.user_type == UserTypeEnum.ADMIN.code:
            user_info_list = await self.admin_user_service.get_user_info_list_by_ids(final_user_ids)
        else:
            logger.warning(
                f"【NoticeServiceImpl】用户类型 {notice.user_type} 暂不支持批量获取用户信息, 通知ID: {notice_id}, 跳过发送"
            )
        if not user_info_list:
            return
        has_user = bool(user_ids)
        has_dept = bool(dept_ids)
        if has_user and has_dept:
            push_target_type = NoticePushTargetTypeEnum.MIXED.code
        elif has_dept:
            push_target_type = NoticePushTargetTypeEnum.DEPT.code
        else:
            push_target_type = NoticePushTargetTypeEnum.USER.code
        target_dept_names = None
        if dept_ids:
            dept_name_list = []
            for dept_id in dept_ids:
                dept = await self.dept_service.get_dept(dept_id)
                if dept:
                    dept_name_list.append(dept.name)
            target_dept_names = dept_name_list if dept_name_list else None
        identity = self.security.current()
        publisher_info = (
            None
            if identity is None
            else {"id": int(identity.account_id), "nickname": None, "avatar": None}
        )
        notice_log_id = await self.notice_log_service.create_notice_log(
            NoticeLogCreateBO(
                notice_id=notice_id,
                notice_title=notice.title,
                notice_type=notice.type,
                push_target_type=push_target_type,
                target_user_ids=[int(uid) for uid in user_ids] if user_ids else None,
                target_dept_ids=dept_ids if dept_ids else None,
                target_dept_names=target_dept_names,
                push_channels=notice.channels,
                total_count=len(user_info_list),
                publisher_info=publisher_info,
            )
        )
        await self._dispatch_notification(notice, user_info_list, notice_log_id, publisher_info)
        logger.info(
            f"【NoticeServiceImpl】通知分发完成, 通知ID: {notice_id}, 目标用户: {len(user_info_list)}, 日志ID: {notice_log_id}"
        )

    async def _dispatch_notification(
        self, notice: NoticeDO, user_info_list, notice_log_id: int, publisher_info
    ) -> None:
        """等待消息持久化和渠道提交；失败必须反馈给调用方。"""
        failed_user_ids = await self.notification_dispatcher.send_notification(
            notice,
            user_info_list,
            NotificationDispatchContext(
                notice_log_id=notice_log_id,
                publisher_info=NoticePublisherInfoDTO.from_raw(publisher_info),
            ),
        )
        if failed_user_ids:
            raise ServiceException(
                GlobalErrorCodeConstants.SERVICE_UNAVAILABLE,
                msg=f"通知分发失败，未成功接收人数：{len(failed_user_ids)}",
            )

    @override
    async def send_notice_direct(self, req: NoticeSendDTO) -> int:
        """基于内置通知模板发送动态通知"""
        if not req.user_ids:
            raise ServiceException(ErrorCodeConstants.NOTICE_SEND_USER_NOT_EXISTS)
        template = await self.notice_mapper.select_by_code(req.notice_code)
        if template is None:
            logger.error(f"【NoticeServiceImpl】未找到内置通知模板, code={req.notice_code}")
            raise ServiceException(ErrorCodeConstants.NOTICE_NOT_FOUND)
        notice = NoticeDO(
            id=template.id,
            title=req.title,
            content=req.content,
            type=template.type,
            user_type=template.user_type,
            channels=template.channels if req.channels is None else req.channels,
            sms_template_code=template.sms_template_code,
            mail_account_id=template.mail_account_id,
        )
        user_info_list = await self.admin_user_service.get_user_info_list_by_ids(req.user_ids)
        if not user_info_list:
            logger.warning(
                f"【NoticeServiceImpl】send_notice_direct: 未找到用户信息, user_ids={req.user_ids}"
            )
            raise ServiceException(ErrorCodeConstants.NOTICE_SEND_USER_NOT_EXISTS)
        notice_log_id = await self.notice_log_service.create_notice_log(
            NoticeLogCreateBO(
                notice_id=notice.id,
                notice_title=req.title,
                notice_type=notice.type,
                push_target_type=NoticePushTargetTypeEnum.USER.code,
                target_user_ids=req.user_ids,
                target_dept_ids=None,
                target_dept_names=None,
                push_channels=notice.channels,
                total_count=len(user_info_list),
                publisher_info=req.publisher_info,
            )
        )
        await self._dispatch_notification(notice, user_info_list, notice_log_id, req.publisher_info)
        logger.info(
            f"【NoticeServiceImpl】动态通知分发完成, 模板: {req.notice_code}, 目标用户: {len(user_info_list)}"
        )
        return notice.id

    async def _validate_for_update(self, id: int | None) -> None:
        """校验通知是否存在且非内置"""
        if id is None:
            return
        notice = await self.notice_mapper.select_by_id(id)
        if notice is None:
            raise ServiceException(ErrorCodeConstants.NOTICE_NOT_FOUND)
        if notice.builtin == BuiltinTypeEnum.BUILTIN.code:
            raise ServiceException(ErrorCodeConstants.NOTICE_CAN_NOT_UPDATE_SYSTEM_TYPE)
