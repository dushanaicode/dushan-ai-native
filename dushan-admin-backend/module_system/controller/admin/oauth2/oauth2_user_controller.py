from fastapi import APIRouter, Depends

from framework.starter_di.decorators.di_dependency import DiDependency
from framework.starter_security.context.security_context import SecurityContext
from framework.starter_security.enums.security_realm import SecurityRealm
from framework.starter_web.response.result import Result
from framework.starter_web.routing.route_policy import RoutePolicy
from module_system.controller.admin.oauth2.vo.user.dept import Dept
from module_system.controller.admin.oauth2.vo.user.post import Post
from module_system.controller.admin.oauth2.vo.user.user_info_resp_vo import OAuth2UserInfoRespVO
from module_system.controller.admin.oauth2.vo.user.user_update_req_vo import OAuth2UserUpdateReqVO
from module_system.controller.admin.user.vo.profile.profile_update_req_vo import (
    UserProfileUpdateReqVO,
)
from module_system.dal.dataobject.user.admin_user_do import AdminUserDO
from module_system.service.dept.dept_service import DeptService
from module_system.service.dept.post_service import PostService
from module_system.service.user.admin_user_service import AdminUserService

oauth2_user_controller = APIRouter(prefix="/oauth2/user", tags=["System - OAuth2 用户管理"])


class Oauth2UserController:
    @staticmethod
    @oauth2_user_controller.get("/get", summary="获得用户基本信息")
    @RoutePolicy(scopes=("user.read",), tenant_required=True, realm=SecurityRealm.TENANT)
    async def get_user_info(
        admin_user_service: AdminUserService = Depends(DiDependency(AdminUserService)),
        dept_service: DeptService = Depends(DiDependency(DeptService)),
        post_service: PostService = Depends(DiDependency(PostService)),
        security: SecurityContext = Depends(DiDependency(SecurityContext)),
    ) -> Result[OAuth2UserInfoRespVO]:
        login_user_id = int(security.require().account_id)
        user: AdminUserDO = await admin_user_service.get_user(login_user_id)
        resp: OAuth2UserInfoRespVO = OAuth2UserInfoRespVO(
            id=user.id,
            username=user.username,
            nickname=user.nickname,
            email=user.email,
            mobile=user.mobile,
            sex=user.sex,
            avatar=user.avatar,
        )
        if user.dept_id is not None:
            dept = await dept_service.get_dept(user.dept_id)
            if dept:
                resp.dept = Dept(id=dept.id, name=dept.name)
        if user.post_ids is not None:
            posts = await post_service.get_post_list(user.post_ids)
            resp.posts = [Post(id=post.id, name=post.name) for post in posts]
        return Result.success(data=resp)

    @staticmethod
    @oauth2_user_controller.put("/update", summary="更新用户基本信息")
    @RoutePolicy(scopes=("user.write",), tenant_required=True, realm=SecurityRealm.TENANT)
    async def update_user_info(
        req_vo: OAuth2UserUpdateReqVO,
        admin_user_service: AdminUserService = Depends(DiDependency(AdminUserService)),
        security: SecurityContext = Depends(DiDependency(SecurityContext)),
    ) -> Result[bool]:
        login_user_id = int(security.require().account_id)
        update_vo = UserProfileUpdateReqVO.model_validate(req_vo.model_dump())
        await admin_user_service.update_user_profile(login_user_id, update_vo)
        return Result.success(data=True)
