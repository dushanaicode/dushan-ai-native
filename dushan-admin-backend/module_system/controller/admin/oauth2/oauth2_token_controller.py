from fastapi import APIRouter, Depends, Query

from framework.common.page.schemas.page_result import PageResult
from framework.common.schemas.request.id_list_req_vo import IdListReqVO
from framework.starter_di.decorators.di_dependency import DiDependency
from framework.starter_security.enums.security_realm import SecurityRealm
from framework.starter_web.response.result import Result
from framework.starter_web.routing.route_policy import RoutePolicy
from module_system.controller.admin.oauth2.vo.token.token_access_token_delete_req_vo import (
    OAuth2AccessTokenDeleteReqVO,
)
from module_system.controller.admin.oauth2.vo.token.token_access_token_page_req_vo import (
    OAuth2AccessTokenPageReqVO,
)
from module_system.controller.admin.oauth2.vo.token.token_access_token_resp_vo import (
    OAuth2AccessTokenRespVO,
)
from module_system.dal.dataobject.oauth2.oauth2_access_token_do import OAuth2AccessTokenDO
from module_system.service.oauth2.oauth2_token_service import OAuth2TokenService

oauth2_token_controller = APIRouter(prefix="/oauth2/token", tags=["System - OAuth2 令牌管理"])


class Oauth2TokenController:
    @staticmethod
    @oauth2_token_controller.get("/page", summary="获得访问令牌分页")
    @RoutePolicy(
        permissions=("system:oauth2:token:page",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def get_access_token_page(
        page_req_vo: OAuth2AccessTokenPageReqVO = Query(),
        oauth2_token_service: OAuth2TokenService = Depends(DiDependency(OAuth2TokenService)),
    ) -> Result[PageResult[OAuth2AccessTokenRespVO]]:
        page_result: PageResult[
            OAuth2AccessTokenDO
        ] = await oauth2_token_service.get_access_token_page(page_req_vo)
        resp_vo: PageResult[OAuth2AccessTokenRespVO] = page_result.convert(OAuth2AccessTokenRespVO)
        return Result.success(data=resp_vo)

    @staticmethod
    @oauth2_token_controller.delete("/delete", summary="删除访问令牌")
    @RoutePolicy(
        permissions=("system:oauth2:token:delete",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def delete_access_token(
        req_vo: OAuth2AccessTokenDeleteReqVO = Query(),
        oauth2_token_service: OAuth2TokenService = Depends(DiDependency(OAuth2TokenService)),
    ) -> Result[bool]:
        await oauth2_token_service.remove_access_token_batch([req_vo.id])
        return Result.success(data=True)

    @staticmethod
    @oauth2_token_controller.delete("/delete-list", summary="批量删除访问令牌")
    @RoutePolicy(
        permissions=("system:oauth2:token:delete",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def delete_access_token_batch(
        req_vo: IdListReqVO = Query(),
        oauth2_token_service: OAuth2TokenService = Depends(DiDependency(OAuth2TokenService)),
    ) -> Result[int]:
        ids = req_vo.ids
        deleted_count = await oauth2_token_service.remove_access_token_batch(ids)
        return Result.success(data=deleted_count)
