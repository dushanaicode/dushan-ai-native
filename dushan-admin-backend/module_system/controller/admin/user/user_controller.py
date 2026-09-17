from fastapi import APIRouter, Body, Depends, Form, Query, Request
from fastapi.responses import StreamingResponse

from framework.common.contracts.snowflake_id import SnowflakeIdStr
from framework.common.enums.status_enum import StatusEnum
from framework.common.page.config.page_settings import PageSettings
from framework.common.page.schemas.page_result import PageResult
from framework.common.schemas.request.id_list_req_vo import IdListReqVO
from framework.starter_di.decorators.di_dependency import DiDependency
from framework.starter_excel.model.excel_providers import ExcelProviders
from framework.starter_excel.reader.excel_reader import ExcelReader
from framework.starter_excel.spi.dict_data_provider import DictDataProvider
from framework.starter_excel.writer.excel_writer import ExcelWriter
from framework.starter_security.enums.security_realm import SecurityRealm
from framework.starter_web.response.file_result import FileResult
from framework.starter_web.response.result import Result
from framework.starter_web.routing.route_policy import RoutePolicy
from framework.starter_web.utils.request_utils import RequestUtils
from module_system.controller.admin.user.vo.user.user_import_excel_vo import UserImportExcelVO
from module_system.controller.admin.user.vo.user.user_import_req_vo import UserImportReqVO
from module_system.controller.admin.user.vo.user.user_import_resp_vo import UserImportRespVO
from module_system.controller.admin.user.vo.user.user_page_req_vo import UserPageReqVO
from module_system.controller.admin.user.vo.user.user_resp_vo import UserRespVO
from module_system.controller.admin.user.vo.user.user_save_req_vo import UserSaveReqVO
from module_system.controller.admin.user.vo.user.user_simple_resp_vo import UserSimpleRespVO
from module_system.controller.admin.user.vo.user.user_update_password_req_vo import (
    UserUpdatePasswordReqVO,
)
from module_system.controller.admin.user.vo.user.user_update_status_req_vo import (
    UserUpdateStatusReqVO,
)
from module_system.convert.user.user_convert import UserConvert
from module_system.dal.dataobject.dept.dept_do import DeptDO
from module_system.dal.dataobject.user.admin_user_do import AdminUserDO
from module_system.definitions.enums.common.common_sex_enum import CommonSexEnum
from module_system.definitions.vo.id_req_vo import IdReqVO
from module_system.service.dept.dept_service import DeptService
from module_system.service.user.admin_user_service import AdminUserService
from module_system.spi.dept.dept_info_provider_adapter import DeptInfoProviderAdapter
from module_system.spi.dept.post_info_provider_adapter import PostInfoProviderAdapter

user_controller = APIRouter(prefix="/user", tags=["System - 用户管理"])


class UserController:
    @staticmethod
    @user_controller.post("/create", summary="新增用户")
    @RoutePolicy(
        permissions=("system:user:create",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def create_user(
        req_vo: UserSaveReqVO = Body(...),
        user_service: AdminUserService = Depends(DiDependency(AdminUserService)),
    ) -> Result[SnowflakeIdStr]:
        user_id: int = await user_service.create_user(req_vo)
        return Result.success(data=user_id)

    @staticmethod
    @user_controller.put("/update", summary="修改用户")
    @RoutePolicy(
        permissions=("system:user:update",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def update_user(
        req_vo: UserSaveReqVO = Body(...),
        user_service: AdminUserService = Depends(DiDependency(AdminUserService)),
    ) -> Result[bool]:
        await user_service.update_user(req_vo)
        return Result.success(data=True)

    @staticmethod
    @user_controller.delete("/delete", summary="删除用户")
    @RoutePolicy(
        permissions=("system:user:delete",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def delete_user(
        req_vo: IdReqVO = Query(),
        user_service: AdminUserService = Depends(DiDependency(AdminUserService)),
    ) -> Result[bool]:
        await user_service.delete_user(req_vo.id)
        return Result.success(data=True)

    @staticmethod
    @user_controller.delete("/delete-list", summary="批量删除用户")
    @RoutePolicy(
        permissions=("system:user:delete",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def delete_user_batch(
        req_vo: IdListReqVO = Query(),
        user_service: AdminUserService = Depends(DiDependency(AdminUserService)),
    ) -> Result[int]:
        deleted_count = await user_service.delete_user_batch(req_vo.ids)
        return Result.success(data=deleted_count)

    @staticmethod
    @user_controller.put("/update-password", summary="重置用户密码")
    @RoutePolicy(
        permissions=("system:user:update-password",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def update_user_password(
        req_vo: UserUpdatePasswordReqVO = Body(...),
        user_service: AdminUserService = Depends(DiDependency(AdminUserService)),
    ) -> Result[bool]:
        await user_service.update_user_password(req_vo.id, req_vo.password)
        return Result.success(data=True)

    @staticmethod
    @user_controller.put("/update-status", summary="修改用户状态")
    @RoutePolicy(
        permissions=("system:user:update",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def update_user_status(
        req_vo: UserUpdateStatusReqVO = Body(...),
        user_service: AdminUserService = Depends(DiDependency(AdminUserService)),
    ) -> Result[bool]:
        await user_service.update_user_status(req_vo.id, req_vo.status)
        return Result.success(data=True)

    @staticmethod
    @user_controller.get("/page", summary="获得用户分页列表")
    @RoutePolicy(
        permissions=("system:user:query",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def get_user_page(
        page_req_vo: UserPageReqVO = Query(),
        user_service: AdminUserService = Depends(DiDependency(AdminUserService)),
        dept_service: DeptService = Depends(DiDependency(DeptService)),
    ) -> Result[PageResult[UserRespVO]]:
        page_result: PageResult[AdminUserDO] = await user_service.get_user_page(page_req_vo)
        dept_map: dict[int, DeptDO] = await dept_service.get_dept_map(
            [user.dept_id for user in page_result.items if user.dept_id]
        )
        converted_list: list[UserRespVO] = [
            UserConvert.convert(user, dept_map.get(user.dept_id)) for user in page_result.items
        ]
        page_result_response: PageResult[UserRespVO] = PageResult[UserRespVO](
            items=converted_list, total=page_result.total
        )
        return Result.success(data=page_result_response)

    @staticmethod
    @user_controller.get(
        "/simple-list",
        summary="获取用户精简信息列表",
        description="只包含被开启的用户，主要用于前端的下拉选项",
    )
    @RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT)
    async def get_simple_user_list(
        user_service: AdminUserService = Depends(DiDependency(AdminUserService)),
        dept_service: DeptService = Depends(DiDependency(DeptService)),
    ) -> Result[list[UserSimpleRespVO]]:
        list_data: list[AdminUserDO] = await user_service.get_user_list_by_status(
            StatusEnum.ENABLE.code
        )
        dept_map: dict[int, DeptDO] = await dept_service.get_dept_map(
            [user.dept_id for user in list_data if user.dept_id]
        )
        simple_list: list[UserSimpleRespVO] = UserConvert.convert_simple_list(list_data, dept_map)
        return Result.success(data=simple_list)

    @staticmethod
    @user_controller.get("/get", summary="获得用户详情")
    @RoutePolicy(
        permissions=("system:user:query",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def get_user(
        req_vo: IdReqVO = Query(),
        user_service: AdminUserService = Depends(DiDependency(AdminUserService)),
        dept_service: DeptService = Depends(DiDependency(DeptService)),
    ) -> Result[UserRespVO]:
        user: AdminUserDO | None = await user_service.get_user(req_vo.id)
        if user is None:
            return Result.success(data=None)
        dept: DeptDO | None = await dept_service.get_dept(user.dept_id)
        user_resp: UserRespVO = UserConvert.convert(user, dept)
        return Result.success(data=user_resp)

    @staticmethod
    @user_controller.get("/export-fields", summary="获取用户可导出字段列表")
    @RoutePolicy(
        permissions=("system:user:export",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def get_export_user_fields() -> Result[list[dict[str, str]]]:
        export_fields = ExcelWriter.export_fields(UserRespVO)
        return Result.success(data=export_fields)

    @staticmethod
    @user_controller.get("/export-excel", summary="导出用户", response_class=StreamingResponse)
    @RoutePolicy(
        permissions=("system:user:export",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def export_user_list(
        request: Request,
        user_service: AdminUserService = Depends(DiDependency(AdminUserService)),
        dept_service: DeptService = Depends(DiDependency(DeptService)),
        excel_writer: ExcelWriter = Depends(DiDependency(ExcelWriter)),
        files: FileResult = Depends(DiDependency(FileResult)),
        dictionaries: DictDataProvider = Depends(DiDependency(DictDataProvider)),
        departments: DeptInfoProviderAdapter = Depends(DiDependency(DeptInfoProviderAdapter)),
        posts: PostInfoProviderAdapter = Depends(DiDependency(PostInfoProviderAdapter)),
        page_settings: PageSettings = Depends(DiDependency(PageSettings)),
    ) -> StreamingResponse:
        excel_providers = ExcelProviders(
            dictionaries=dictionaries, departments=departments, posts=posts
        )
        page_req_vo: UserPageReqVO = RequestUtils.validate_with_auto_list_params(
            request, UserPageReqVO
        )
        page_req_vo.enable_fetch_all(
            max_rows=min(excel_writer.settings.max_export_rows, page_settings.fetch_all_max_rows)
        )
        list_data_page: PageResult[AdminUserDO] = await user_service.get_user_page(page_req_vo)
        list_data: list[AdminUserDO] = list_data_page.items
        dept_map: dict[int, DeptDO] = await dept_service.get_dept_map(
            [user.dept_id for user in list_data if user.dept_id]
        )
        user_resp_list: list[UserRespVO] = [
            UserConvert.convert(user, dept_map.get(user.dept_id)) for user in list_data
        ]
        filename = "用户数据"
        file_data = await excel_writer.write(
            "数据", UserRespVO, user_resp_list, providers=excel_providers, fields=page_req_vo.fields
        )
        return files.excel_stream(file_data, file_name=f"{filename}.xlsx")

    @staticmethod
    @user_controller.get("/get-import-template", summary="获得导入用户模板")
    @RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT)
    async def import_template(
        excel_writer: ExcelWriter = Depends(DiDependency(ExcelWriter)),
        files: FileResult = Depends(DiDependency(FileResult)),
        dictionaries: DictDataProvider = Depends(DiDependency(DictDataProvider)),
        departments: DeptInfoProviderAdapter = Depends(DiDependency(DeptInfoProviderAdapter)),
        posts: PostInfoProviderAdapter = Depends(DiDependency(PostInfoProviderAdapter)),
    ) -> StreamingResponse:
        excel_providers = ExcelProviders(
            dictionaries=dictionaries, departments=departments, posts=posts
        )
        filename = "用户导入模板"
        list_data: list[UserImportExcelVO] = [
            UserImportExcelVO(
                username="dushan1",
                dept_id=1,
                email="ds1@qq.com",
                mobile="15666666666",
                nickname="渡山1",
                status=StatusEnum.ENABLE.code,
                sex=CommonSexEnum.FEMALE.code,
            ),
            UserImportExcelVO(
                username="dushan2",
                dept_id=2,
                email="ds2@qq.com",
                mobile="15777777777",
                nickname="渡山2",
                status=StatusEnum.DISABLE.code,
                sex=CommonSexEnum.MALE.code,
            ),
        ]
        file_data = await excel_writer.write(
            "用户列表", UserImportExcelVO, list_data, providers=excel_providers
        )
        return files.excel_stream(file_data, file_name=f"{filename}.xlsx")

    @staticmethod
    @user_controller.post("/import", summary="导入用户")
    @RoutePolicy(
        permissions=("system:user:import",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def import_excel(
        req_vo: UserImportReqVO = Form(media_type="multipart/form-data"),
        user_service: AdminUserService = Depends(DiDependency(AdminUserService)),
        excel_reader: ExcelReader = Depends(DiDependency(ExcelReader)),
        dictionaries: DictDataProvider = Depends(DiDependency(DictDataProvider)),
        departments: DeptInfoProviderAdapter = Depends(DiDependency(DeptInfoProviderAdapter)),
        posts: PostInfoProviderAdapter = Depends(DiDependency(PostInfoProviderAdapter)),
    ) -> Result[UserImportRespVO]:
        file = req_vo.file
        update_support = req_vo.update_support
        excel_providers = ExcelProviders(
            dictionaries=dictionaries, departments=departments, posts=posts
        )
        import_users: list[UserImportExcelVO] = await excel_reader.read(
            file, UserImportExcelVO, providers=excel_providers
        )
        import_resp: UserImportRespVO = await user_service.import_user_list(
            import_users, update_support
        )
        return Result.success(data=import_resp)
