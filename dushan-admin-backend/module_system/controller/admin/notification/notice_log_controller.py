from fastapi import APIRouter, Depends, Query

from framework.common.page.schemas.page_result import PageResult
from framework.starter_di.decorators.di_dependency import DiDependency
from framework.starter_security.enums.security_realm import SecurityRealm
from framework.starter_web.response.result import Result
from framework.starter_web.routing.route_policy import RoutePolicy
from module_system.api.user.admin_user_api import AdminUserApi
from module_system.controller.admin.notification.vo.notice_log.notice_log_detail_resp_vo import (
    NoticeLogDetailRespVO,
)
from module_system.controller.admin.notification.vo.notice_log.notice_log_page_req_vo import (
    NoticeLogPageReqVO,
)
from module_system.controller.admin.notification.vo.notice_log.notice_log_resp_vo import (
    NoticeLogRespVO,
)
from module_system.convert.notification.notice_log_convert import NoticeLogConvert
from module_system.dal.dataobject.notification.notice_log_do import NoticeLogDO
from module_system.definitions.vo.id_req_vo import IdReqVO
from module_system.service.notification.notice_log_service import (
    NoticeLogService,
)

notice_log_controller = APIRouter(prefix="/notification/log", tags=["System - 通知日志管理"])


class NoticeLogController:
    @staticmethod
    @notice_log_controller.get("/page", summary="获得通知日志分页")
    @RoutePolicy(
        permissions=("system:notification:log:query",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def get_notice_log_page(
        page_req_vo: NoticeLogPageReqVO = Query(),
        service: NoticeLogService = Depends(DiDependency(NoticeLogService)),
    ) -> Result[PageResult[NoticeLogRespVO]]:
        page_result: PageResult[NoticeLogDO] = await service.get_notice_log_page(page_req_vo)
        resp_vo: PageResult[NoticeLogRespVO] = page_result.convert(NoticeLogRespVO)
        return Result.success(data=resp_vo)

    @staticmethod
    @notice_log_controller.get("/get", summary="获得通知日志详情（含消息明细）")
    @RoutePolicy(
        permissions=("system:notification:log:query",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def get_notice_log_detail(
        req_vo: IdReqVO = Query(),
        service: NoticeLogService = Depends(DiDependency(NoticeLogService)),
        user_api: AdminUserApi = Depends(DiDependency(AdminUserApi)),
    ) -> Result[NoticeLogDetailRespVO]:
        notice_log = await service.get_notice_log(req_vo.id)
        if notice_log is None:
            return Result.success(data=None)
        messages = await service.get_notice_log_messages(req_vo.id)
        user_ids = list({msg.user_id for msg in messages})
        user_map = await user_api.get_user_map(user_ids) if user_ids else {}
        detail = NoticeLogConvert.convert_detail(notice_log, messages, user_map)
        return Result.success(data=detail)
