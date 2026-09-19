from fastapi import APIRouter, Depends, Query

from framework.common.contracts import SnowflakeIdStr
from framework.common.page import PageResult
from framework.common.schemas.request import IdListReqVO, IdReqVO, UpdateStatusReqVO
from framework.starter_di.public import (
    DiDependency,
)
from framework.starter_security.public import (
    SecurityRealm,
)
from framework.starter_web.public import (
    Result,
    RoutePolicy,
)
from module_system.controller.admin.notification.vo.notice.notice_page_req_vo import NoticePageReqVO
from module_system.controller.admin.notification.vo.notice.notice_resp_vo import NoticeRespVO
from module_system.controller.admin.notification.vo.notice.notice_save_req_vo import NoticeSaveReqVO
from module_system.controller.admin.notification.vo.notice.notice_send_req_vo import NoticeSendReqVO
from module_system.dal.dataobject.notification.notice_do import NoticeDO
from module_system.service.notification.notice_service import NoticeService

notice_controller = APIRouter(prefix="/notification", tags=["System - 系统通知管理"])


class NoticeController:
    @staticmethod
    @notice_controller.post("/create", summary="创建系统通知")
    @RoutePolicy(
        permissions=("system:notification:create",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def create_notice(
        create_req_vo: NoticeSaveReqVO,
        notice_service: NoticeService = Depends(DiDependency(NoticeService)),
    ) -> Result[SnowflakeIdStr]:
        notice_id = await notice_service.create_notice(create_req_vo)
        return Result.success(data=notice_id)

    @staticmethod
    @notice_controller.put("/update", summary="更新系统通知")
    @RoutePolicy(
        permissions=("system:notification:update",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def update_notice(
        update_req_vo: NoticeSaveReqVO,
        notice_service: NoticeService = Depends(DiDependency(NoticeService)),
    ) -> Result[bool]:
        await notice_service.update_notice(update_req_vo)
        return Result.success(data=True)

    @staticmethod
    @notice_controller.put("/update-status", summary="修改系统通知状态")
    @RoutePolicy(
        permissions=("system:notification:update",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def update_notice_status(
        req_vo: UpdateStatusReqVO,
        notice_service: NoticeService = Depends(DiDependency(NoticeService)),
    ) -> Result[bool]:
        await notice_service.update_status(req_vo.id, req_vo.status)
        return Result.success(data=True)

    @staticmethod
    @notice_controller.delete("/delete", summary="删除系统通知")
    @RoutePolicy(
        permissions=("system:notification:delete",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def delete_notice(
        req_vo: IdReqVO = Query(),
        notice_service: NoticeService = Depends(DiDependency(NoticeService)),
    ) -> Result[bool]:
        await notice_service.delete_notice(req_vo.id)
        return Result.success(data=True)

    @staticmethod
    @notice_controller.delete("/delete-list", summary="批量删除系统通知")
    @RoutePolicy(
        permissions=("system:notification:delete",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def delete_notice_batch(
        req_vo: IdListReqVO = Query(),
        notice_service: NoticeService = Depends(DiDependency(NoticeService)),
    ) -> Result[int]:
        deleted_count = await notice_service.delete_notice_batch(req_vo.ids)
        return Result.success(data=deleted_count)

    @staticmethod
    @notice_controller.get("/page", summary="获取系统通知分页")
    @RoutePolicy(
        permissions=("system:notification:query",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def get_notice_page(
        page_req_vo: NoticePageReqVO = Query(),
        notice_service: NoticeService = Depends(DiDependency(NoticeService)),
    ) -> Result[PageResult[NoticeRespVO]]:
        page_result: PageResult[NoticeDO] = await notice_service.get_notice_page(page_req_vo)
        resp_vo: PageResult[NoticeRespVO] = page_result.convert(NoticeRespVO)
        return Result.success(data=resp_vo)

    @staticmethod
    @notice_controller.get("/get", summary="获取系统通知")
    @RoutePolicy(
        permissions=("system:notification:query",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def get_notice(
        req_vo: IdReqVO = Query(),
        notice_service: NoticeService = Depends(DiDependency(NoticeService)),
    ) -> Result[NoticeRespVO]:
        notice = await notice_service.get_notice(req_vo.id)
        data = NoticeRespVO.model_validate(notice)
        return Result.success(data=data)

    @staticmethod
    @notice_controller.post("/push-targets", summary="定向推送系统通知")
    @RoutePolicy(
        permissions=("system:notification:send",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def push_notice_targets(
        req_vo: NoticeSendReqVO,
        notice_service: NoticeService = Depends(DiDependency(NoticeService)),
    ) -> Result[bool]:
        await notice_service.send_notice(req_vo)
        return Result.success(data=True)
