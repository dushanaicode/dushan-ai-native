from fastapi import APIRouter, Depends, Query

from framework.common.contracts import SnowflakeIdStr
from framework.common.page import PageResult
from framework.common.schemas.request import IdListReqVO, IdReqVO
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
from module_system.controller.admin.announcement.vo.announcement_page_req_vo import (
    AnnouncementPageReqVO,
)
from module_system.controller.admin.announcement.vo.announcement_resp_vo import (
    AnnouncementRespVO,
)
from module_system.controller.admin.announcement.vo.announcement_save_req_vo import (
    AnnouncementSaveReqVO,
)
from module_system.dal.dataobject.announcement.announcement_do import AnnouncementDO
from module_system.service.announcement.announcement_service import (
    AnnouncementService,
)

announcement_controller = APIRouter(prefix="/announcement", tags=["System - 公告管理"])


class AnnouncementController:
    @staticmethod
    @announcement_controller.post("/create", summary="创建公告")
    @RoutePolicy(
        permissions=("system:announcement:create",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def create_announcement(
        create_req_vo: AnnouncementSaveReqVO,
        announcement_service: AnnouncementService = Depends(DiDependency(AnnouncementService)),
    ) -> Result[SnowflakeIdStr]:
        announcement_id = await announcement_service.create_announcement(create_req_vo)
        return Result.success(data=announcement_id)

    @staticmethod
    @announcement_controller.put("/update", summary="更新公告")
    @RoutePolicy(
        permissions=("system:announcement:update",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def update_announcement(
        update_req_vo: AnnouncementSaveReqVO,
        announcement_service: AnnouncementService = Depends(DiDependency(AnnouncementService)),
    ) -> Result[bool]:
        await announcement_service.update_announcement(update_req_vo)
        return Result.success(data=True)

    @staticmethod
    @announcement_controller.delete("/delete", summary="删除公告")
    @RoutePolicy(
        permissions=("system:announcement:delete",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def delete_announcement(
        req_vo: IdReqVO = Query(),
        announcement_service: AnnouncementService = Depends(DiDependency(AnnouncementService)),
    ) -> Result[bool]:
        await announcement_service.delete_announcement(req_vo.id)
        return Result.success(data=True)

    @staticmethod
    @announcement_controller.delete("/delete-list", summary="批量删除公告")
    @RoutePolicy(
        permissions=("system:announcement:delete",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def delete_announcement_batch(
        req_vo: IdListReqVO = Query(),
        announcement_service: AnnouncementService = Depends(DiDependency(AnnouncementService)),
    ) -> Result[int]:
        deleted_count = await announcement_service.delete_announcement_batch(req_vo.ids)
        return Result.success(data=deleted_count)

    @staticmethod
    @announcement_controller.get("/page", summary="获取公告分页")
    @RoutePolicy(
        permissions=("system:announcement:query",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def get_announcement_page(
        page_req_vo: AnnouncementPageReqVO = Query(),
        announcement_service: AnnouncementService = Depends(DiDependency(AnnouncementService)),
    ) -> Result[PageResult[AnnouncementRespVO]]:
        page_result: PageResult[AnnouncementDO] = await announcement_service.get_announcement_page(
            page_req_vo
        )
        resp_vo: PageResult[AnnouncementRespVO] = page_result.convert(AnnouncementRespVO)
        return Result.success(data=resp_vo)

    @staticmethod
    @announcement_controller.get("/get", summary="获取公告")
    @RoutePolicy(
        permissions=("system:announcement:query",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def get_announcement(
        req_vo: IdReqVO = Query(),
        announcement_service: AnnouncementService = Depends(DiDependency(AnnouncementService)),
    ) -> Result[AnnouncementRespVO]:
        announcement = await announcement_service.get_announcement(req_vo.id)
        data = AnnouncementRespVO.model_validate(announcement)
        return Result.success(data=data)

    @staticmethod
    @announcement_controller.post("/publish", summary="立即发布公告")
    @RoutePolicy(
        permissions=("system:announcement:update",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def publish_announcement(
        req_vo: IdReqVO = Query(),
        announcement_service: AnnouncementService = Depends(DiDependency(AnnouncementService)),
    ) -> Result[bool]:
        result = await announcement_service.publish_announcement(req_vo.id)
        return Result.success(data=result)

    @staticmethod
    @announcement_controller.post("/schedule-publish", summary="调度定时发布公告")
    @RoutePolicy(
        permissions=("system:announcement:update",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def schedule_announcement_publish(
        req_vo: IdReqVO = Query(),
        announcement_service: AnnouncementService = Depends(DiDependency(AnnouncementService)),
    ) -> Result[bool]:
        result = await announcement_service.schedule_announcement_publish(req_vo.id)
        return Result.success(data=result)
