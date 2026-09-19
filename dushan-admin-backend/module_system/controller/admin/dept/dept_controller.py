from fastapi import APIRouter, Depends, Query

from framework.common.contracts import SnowflakeIdStr
from framework.common.enums import StatusEnum
from framework.common.exception import ServiceException
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
from module_system.controller.admin.dept.vo.dept.dept_list_req_vo import DeptListReqVO
from module_system.controller.admin.dept.vo.dept.dept_resp_vo import DeptRespVO
from module_system.controller.admin.dept.vo.dept.dept_save_req_vo import DeptSaveReqVO
from module_system.controller.admin.dept.vo.dept.dept_simple_resp_vo import DeptSimpleRespVO
from module_system.definitions.constants.error_code_constants import ErrorCodeConstants
from module_system.service.dept.dept_service import DeptService

dept_controller = APIRouter(prefix="/dept", tags=["System - 部门管理"])


class DeptController:
    @staticmethod
    @dept_controller.post("/create", summary="创建部门")
    @RoutePolicy(
        permissions=("system:dept:create",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def create_dept(
        create_req_vo: DeptSaveReqVO, dept_service: DeptService = Depends(DiDependency(DeptService))
    ) -> Result[SnowflakeIdStr]:
        dept_id = await dept_service.create_dept(create_req_vo)
        return Result.success(data=dept_id)

    @staticmethod
    @dept_controller.put("/update", summary="更新部门")
    @RoutePolicy(
        permissions=("system:dept:update",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def update_dept(
        update_req_vo: DeptSaveReqVO, dept_service: DeptService = Depends(DiDependency(DeptService))
    ) -> Result[bool]:
        await dept_service.update_dept(update_req_vo)
        return Result.success(data=True)

    @staticmethod
    @dept_controller.put("/update-status", summary="修改部门状态")
    @RoutePolicy(
        permissions=("system:dept:update",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def update_dept_status(
        req_vo: UpdateStatusReqVO, dept_service: DeptService = Depends(DiDependency(DeptService))
    ) -> Result[bool]:
        await dept_service.update_status(req_vo.id, req_vo.status)
        return Result.success(data=True)

    @staticmethod
    @dept_controller.delete("/delete", summary="删除部门")
    @RoutePolicy(
        permissions=("system:dept:delete",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def delete_dept(
        req_vo: IdReqVO = Query(), dept_service: DeptService = Depends(DiDependency(DeptService))
    ) -> Result[bool]:
        await dept_service.delete_dept(req_vo.id)
        return Result.success(data=True)

    @staticmethod
    @dept_controller.delete("/delete-list", summary="批量删除部门")
    @RoutePolicy(
        permissions=("system:dept:delete",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def delete_dept_batch(
        req_vo: IdListReqVO = Query(),
        dept_service: DeptService = Depends(DiDependency(DeptService)),
    ) -> Result[int]:
        deleted_count = await dept_service.delete_dept_batch(req_vo.ids)
        return Result.success(data=deleted_count)

    @staticmethod
    @dept_controller.get("/list", summary="获取部门列表")
    @RoutePolicy(
        permissions=("system:dept:query",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def get_dept_list(
        req_vo: DeptListReqVO = Query(),
        dept_service: DeptService = Depends(DiDependency(DeptService)),
    ) -> Result[list[DeptRespVO]]:
        dept_list = await dept_service.get_dept_list(req_vo)
        response = [DeptRespVO.model_validate(dept) for dept in dept_list]
        return Result.success(data=response)

    @staticmethod
    @dept_controller.get("/simple-list", include_in_schema=False)
    @RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT)
    async def get_simple_dept_list(
        dept_service: DeptService = Depends(DiDependency(DeptService)),
    ) -> Result[list[DeptSimpleRespVO]]:
        req_vo = DeptListReqVO(status=StatusEnum.ENABLE.code)
        dept_list = await dept_service.get_dept_list(req_vo)
        response = [DeptSimpleRespVO.model_validate(dept) for dept in dept_list]
        return Result.success(data=response)

    @staticmethod
    @dept_controller.get("/get", summary="获得部门信息")
    @RoutePolicy(
        permissions=("system:dept:query",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def get_dept(
        req_vo: IdReqVO = Query(), dept_service: DeptService = Depends(DiDependency(DeptService))
    ) -> Result[DeptRespVO]:
        dept = await dept_service.get_dept(req_vo.id)
        if dept is None:
            raise ServiceException(ErrorCodeConstants.DEPT_NOT_FOUND)
        response = DeptRespVO.model_validate(dept)
        return Result.success(data=response)
