from fastapi import APIRouter, Depends

from framework.common.enums import UserTypeEnum
from framework.starter_di.public import (
    DiDependency,
)
from framework.starter_security.public import (
    SecurityContext,
    SecurityErrorCodes,
    SecurityException,
    SecurityRealm,
)
from framework.starter_web.public import (
    Result,
    RoutePolicy,
)
from module_system.controller.admin.user.vo.profile.online_device_req_vo import OnlineDeviceReqVO
from module_system.controller.admin.user.vo.profile.profile_online_device_vo import (
    ProfileOnlineDeviceVO,
)
from module_system.controller.admin.user.vo.profile.profile_resp_vo import UserProfileRespVO
from module_system.controller.admin.user.vo.profile.profile_update_password_req_vo import (
    UserProfileUpdatePasswordReqVO,
)
from module_system.controller.admin.user.vo.profile.profile_update_req_vo import (
    UserProfileUpdateReqVO,
)
from module_system.convert.user.user_convert import UserConvert
from module_system.dal.dataobject.dept.dept_do import DeptDO
from module_system.dal.dataobject.dept.post_do import PostDO
from module_system.dal.dataobject.permission.role_do import RoleDO
from module_system.dal.dataobject.user.admin_user_do import AdminUserDO
from module_system.dal.dataobject.user.admin_user_profile_do import AdminUserProfileDO
from module_system.service.dept.dept_service import DeptService
from module_system.service.dept.post_service import PostService
from module_system.service.permission.permission_service import PermissionService
from module_system.service.permission.role_service import RoleService
from module_system.service.user.admin_user_service import AdminUserService
from module_system.service.user.user_profile_service import UserProfileService

user_profile_controller = APIRouter(prefix="/user/profile", tags=["System - 用户个人中心"])


class UserProfileController:
    @staticmethod
    @user_profile_controller.get("/get", summary="获得登录用户信息")
    @RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT)
    async def get_user_profile(
        user_service: AdminUserService = Depends(DiDependency(AdminUserService)),
        dept_service: DeptService = Depends(DiDependency(DeptService)),
        post_service: PostService = Depends(DiDependency(PostService)),
        permission_service: PermissionService = Depends(DiDependency(PermissionService)),
        role_service: RoleService = Depends(DiDependency(RoleService)),
        profile_service: UserProfileService = Depends(DiDependency(UserProfileService)),
        security: SecurityContext = Depends(DiDependency(SecurityContext)),
    ) -> Result[UserProfileRespVO]:
        current_user_id: int | None = int(security.require().account_id)
        if current_user_id is None:
            raise SecurityException(SecurityErrorCodes.MISSING)
        user: AdminUserDO | None = await user_service.get_user(current_user_id)
        user_role_ids = await permission_service.get_user_role_id_list_by_user_id(user.id)
        user_roles: list[RoleDO] = await role_service.get_role_list_from_cache(user_role_ids)
        dept: DeptDO | None = await dept_service.get_dept(user.dept_id) if user.dept_id else None
        posts: list[PostDO] | None = (
            await post_service.get_post_list(list(user.post_ids)) if user.post_ids else None
        )
        user_profile: AdminUserProfileDO | None = await profile_service.get_user_profile(user.id)
        user_profile_resp_vo: UserProfileRespVO = UserConvert.convert_profile(
            user, user_roles, dept, posts, user_profile
        )
        return Result.success(data=user_profile_resp_vo)

    @staticmethod
    @user_profile_controller.put("/update", summary="修改用户个人信息")
    @RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT)
    async def update_user_profile(
        req_vo: UserProfileUpdateReqVO,
        admin_user_service: AdminUserService = Depends(DiDependency(AdminUserService)),
        profile_service: UserProfileService = Depends(DiDependency(UserProfileService)),
        security: SecurityContext = Depends(DiDependency(SecurityContext)),
    ) -> Result[bool]:
        user_id: int | None = int(security.require().account_id)
        if user_id is None:
            raise SecurityException(SecurityErrorCodes.MISSING)
        await admin_user_service.update_user_profile(user_id, req_vo)
        await profile_service.create_or_update_profile(user_id, req_vo)
        return Result.success(data=True)

    @staticmethod
    @user_profile_controller.put("/update-password", summary="修改用户个人密码")
    @RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT)
    async def update_user_profile_password(
        req_vo: UserProfileUpdatePasswordReqVO,
        admin_user_service: AdminUserService = Depends(DiDependency(AdminUserService)),
        security: SecurityContext = Depends(DiDependency(SecurityContext)),
    ) -> Result[bool]:
        user_id: int | None = int(security.require().account_id)
        if user_id is None:
            raise SecurityException(SecurityErrorCodes.MISSING)
        await admin_user_service.update_user_password_by_vo(user_id, req_vo)
        return Result.success(data=True)

    @staticmethod
    @user_profile_controller.get("/online-devices", summary="获取我的在线设备列表")
    @RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT)
    async def get_user_online_devices(
        profile_service: UserProfileService = Depends(DiDependency(UserProfileService)),
        security: SecurityContext = Depends(DiDependency(SecurityContext)),
    ) -> Result[list[ProfileOnlineDeviceVO]]:
        login_user = security.require()
        devices: list[ProfileOnlineDeviceVO] = await profile_service.get_user_online_devices(
            login_user,
            UserTypeEnum.ADMIN,
        )
        return Result.success(data=devices)

    @staticmethod
    @user_profile_controller.delete("/online-devices/{tokenId}", summary="踢出在线设备")
    @RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT)
    async def kickout_online_device(
        req_vo: OnlineDeviceReqVO = Depends(OnlineDeviceReqVO.from_path),
        profile_service: UserProfileService = Depends(DiDependency(UserProfileService)),
        security: SecurityContext = Depends(DiDependency(SecurityContext)),
    ) -> Result[bool]:
        current_user_id = int(security.require().account_id)
        if not current_user_id:
            raise SecurityException(SecurityErrorCodes.MISSING)
        await profile_service.kickout_online_device(req_vo.token_id, current_user_id)
        return Result.success(data=True)
