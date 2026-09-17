from fastapi import APIRouter, Body, Depends, Query

from framework.common.enums.user_type_enum import UserTypeEnum
from framework.common.page.schemas.page_result import PageResult
from framework.starter_di.decorators.di_dependency import DiDependency
from framework.starter_security.context.security_context import SecurityContext
from framework.starter_security.enums.security_realm import SecurityRealm
from framework.starter_web.response.result import Result
from framework.starter_web.routing.route_policy import RoutePolicy
from module_system.api.social.dto.social_user_bind_req_dto import SocialUserBindReqDTO
from module_system.controller.admin.social.vo.user.user_bind_req_vo import SocialUserBindReqVO
from module_system.controller.admin.social.vo.user.user_page_req_vo import SocialUserPageReqVO
from module_system.controller.admin.social.vo.user.user_resp_vo import SocialUserRespVO
from module_system.controller.admin.social.vo.user.user_unbind_req_vo import SocialUserUnbindReqVO
from module_system.dal.dataobject.social.social_user_do import SocialUserDO
from module_system.definitions.vo.id_req_vo import IdReqVO
from module_system.service.social.social_user_service import SocialUserService

social_user_controller = APIRouter(prefix="/social/user", tags=["System - 社交用户管理"])


class SocialUserController:
    @staticmethod
    @social_user_controller.post("/bind", summary="社交绑定，使用 code 授权码")
    @RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT)
    async def social_bind(
        req_vo: SocialUserBindReqVO,
        social_user_service: SocialUserService = Depends(DiDependency(SocialUserService)),
        security: SecurityContext = Depends(DiDependency(SecurityContext)),
    ) -> Result[str]:
        command = SocialUserBindReqDTO(
            **req_vo.model_dump(by_alias=False),
            user_id=int(security.require().account_id),
            user_type=UserTypeEnum.ADMIN.code,
        )
        openid = await social_user_service.bind_social_user(command)
        return Result.success(data=openid)

    @staticmethod
    @social_user_controller.delete("/unbind", summary="取消社交绑定")
    @RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT)
    async def social_unbind(
        req_vo: SocialUserUnbindReqVO = Body(...),
        social_user_service: SocialUserService = Depends(DiDependency(SocialUserService)),
        security: SecurityContext = Depends(DiDependency(SecurityContext)),
    ) -> Result[bool]:
        login_user_id = int(security.require().account_id)
        await social_user_service.unbind_social_user(
            user_id=login_user_id,
            user_type=UserTypeEnum.ADMIN.code,
            social_type=req_vo.type,
            openid=req_vo.openid,
        )
        return Result.success(data=True)

    @staticmethod
    @social_user_controller.get("/get", summary="获得社交用户")
    @RoutePolicy(
        permissions=("system:social:user:query",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def get_social_user(
        req_vo: IdReqVO = Query(),
        social_user_service: SocialUserService = Depends(DiDependency(SocialUserService)),
    ) -> Result[SocialUserRespVO]:
        social_user = await social_user_service.get_social_user(req_vo.id)
        if social_user is None:
            return Result.success(data=None)
        data = SocialUserRespVO.model_validate(social_user)
        return Result.success(data=data)

    @staticmethod
    @social_user_controller.get("/page", summary="获得社交用户分页")
    @RoutePolicy(
        permissions=("system:social:user:query",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def get_social_user_page(
        page_req_vo: SocialUserPageReqVO = Query(),
        social_user_service: SocialUserService = Depends(DiDependency(SocialUserService)),
    ) -> Result[PageResult[SocialUserRespVO]]:
        page_result: PageResult[SocialUserDO] = await social_user_service.get_social_user_page(
            page_req_vo
        )
        resp_vo: PageResult[SocialUserRespVO] = page_result.convert(SocialUserRespVO)
        return Result.success(data=resp_vo)

    @staticmethod
    @social_user_controller.get("/get-bind-list", summary="获得绑定社交用户列表")
    @RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT)
    async def get_bind_social_user_list(
        social_user_service: SocialUserService = Depends(DiDependency(SocialUserService)),
        security: SecurityContext = Depends(DiDependency(SecurityContext)),
    ) -> Result[list[SocialUserRespVO]]:
        login_user_id = int(security.require().account_id)
        social_user_dos: list[SocialUserDO] = await social_user_service.get_social_user_list(
            user_id=login_user_id, user_type=UserTypeEnum.ADMIN.code
        )
        data = [SocialUserRespVO.model_validate(user_do) for user_do in social_user_dos]
        return Result.success(data=data)
