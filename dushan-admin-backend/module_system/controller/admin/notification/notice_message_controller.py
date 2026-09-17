from fastapi import APIRouter, Depends, Query

from framework.common.enums.user_type_enum import UserTypeEnum
from framework.common.page.schemas.page_result import PageResult
from framework.common.schemas.request.id_list_req_vo import IdListReqVO
from framework.starter_di.decorators.di_dependency import DiDependency
from framework.starter_security.context.security_context import SecurityContext
from framework.starter_security.enums.security_realm import SecurityRealm
from framework.starter_web.response.result import Result
from framework.starter_web.routing.access_log_policy import AccessLogPolicy
from framework.starter_web.routing.route_policy import RoutePolicy
from module_system.controller.admin.notification.vo.notice_message.notice_message_my_page_req_vo import (
    NoticeMessageMyPageReqVO,
)
from module_system.controller.admin.notification.vo.notice_message.notice_message_page_req_vo import (
    NoticeMessagePageReqVO,
)
from module_system.controller.admin.notification.vo.notice_message.notice_message_resp_vo import (
    NoticeMessageRespVO,
)
from module_system.controller.admin.notification.vo.notice_message.notice_message_unread_list_req_vo import (
    NoticeMessageUnreadListReqVO,
)
from module_system.dal.dataobject.notification.notice_message_do import NoticeMessageDO
from module_system.definitions.vo.id_req_vo import IdReqVO
from module_system.service.notification.notice_message_service import (
    NoticeMessageService,
)

notice_message_controller = APIRouter(
    prefix="/notification/message", tags=["System - 通知消息管理"]
)
ADMIN_USER_TYPE = UserTypeEnum.ADMIN.code


class NoticeMessageController:
    @staticmethod
    @notice_message_controller.get("/get", summary="获得站内信")
    @RoutePolicy(
        permissions=("system:notification:message:query",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def get_notice_message(
        req_vo: IdReqVO = Query(),
        service: NoticeMessageService = Depends(DiDependency(NoticeMessageService)),
    ) -> Result[NoticeMessageRespVO]:
        message = await service.get_notice_message(req_vo.id)
        if message is None:
            return Result.success(data=None)
        data = NoticeMessageRespVO.model_validate(message)
        return Result.success(data=data)

    @staticmethod
    @notice_message_controller.get("/page", summary="获得站内信分页")
    @RoutePolicy(
        permissions=("system:notification:message:query",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def get_notice_message_page(
        page_req_vo: NoticeMessagePageReqVO = Query(),
        service: NoticeMessageService = Depends(DiDependency(NoticeMessageService)),
    ) -> Result[PageResult[NoticeMessageRespVO]]:
        page_result: PageResult[NoticeMessageDO] = await service.get_notice_message_page(
            page_req_vo
        )
        resp_vo: PageResult[NoticeMessageRespVO] = page_result.convert(NoticeMessageRespVO)
        return Result.success(data=resp_vo)

    @staticmethod
    @notice_message_controller.get("/my-page", summary="获得我的站内信分页")
    @RoutePolicy(
        permissions=("system:notification:message:query",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def get_my_notice_message_page(
        page_req_vo: NoticeMessageMyPageReqVO = Query(),
        service: NoticeMessageService = Depends(DiDependency(NoticeMessageService)),
        security: SecurityContext = Depends(DiDependency(SecurityContext)),
    ) -> Result[PageResult[NoticeMessageRespVO]]:
        user_id = int(security.require().account_id)
        page_result = await service.get_my_notice_message_page(
            page_req_vo, user_id, ADMIN_USER_TYPE
        )
        result_page = page_result.convert(NoticeMessageRespVO)
        return Result.success(data=result_page)

    @staticmethod
    @notice_message_controller.put("/update-read", summary="标记站内信为已读")
    @RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT)
    async def update_notice_message_read(
        req_vo: IdListReqVO,
        service: NoticeMessageService = Depends(DiDependency(NoticeMessageService)),
        security: SecurityContext = Depends(DiDependency(SecurityContext)),
    ) -> Result[bool]:
        ids = req_vo.ids
        user_id = int(security.require().account_id)
        await service.update_notice_message_read(ids, user_id, ADMIN_USER_TYPE)
        return Result.success(data=True)

    @staticmethod
    @notice_message_controller.put("/update-all-read", summary="标记所有站内信为已读")
    @RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT)
    async def update_all_notice_message_read(
        service: NoticeMessageService = Depends(DiDependency(NoticeMessageService)),
        security: SecurityContext = Depends(DiDependency(SecurityContext)),
    ) -> Result[bool]:
        user_id = int(security.require().account_id)
        await service.update_all_notice_message_read(user_id, ADMIN_USER_TYPE)
        return Result.success(data=True)

    @staticmethod
    @notice_message_controller.get(
        "/get-unread-list", summary="获取当前用户的最新站内信列表，默认 10 条"
    )
    @RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT)
    async def get_unread_notice_message_list(
        req_vo: NoticeMessageUnreadListReqVO = Query(),
        service: NoticeMessageService = Depends(DiDependency(NoticeMessageService)),
        security: SecurityContext = Depends(DiDependency(SecurityContext)),
    ) -> Result[list[NoticeMessageRespVO]]:
        user_id = int(security.require().account_id)
        messages = await service.get_unread_notice_message_list(
            user_id, ADMIN_USER_TYPE, req_vo.size
        )
        data = [NoticeMessageRespVO.model_validate(item) for item in messages]
        return Result.success(data=data)

    @staticmethod
    @notice_message_controller.get("/get-unread-count", summary="获得当前用户的未读站内信数量")
    @AccessLogPolicy(enabled=False)
    @RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT)
    async def get_unread_notice_message_count(
        service: NoticeMessageService = Depends(DiDependency(NoticeMessageService)),
        security: SecurityContext = Depends(DiDependency(SecurityContext)),
    ) -> Result[int]:
        user_id = int(security.require().account_id)
        count = await service.get_unread_notice_message_count(user_id, ADMIN_USER_TYPE)
        return Result.success(data=count)
