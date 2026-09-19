from typing import Annotated

from fastapi import APIRouter, Depends, Form, Query, Request

from framework.common.dates import DateUtils
from framework.common.enums import UserTypeEnum
from framework.common.exception import (
    GlobalErrorCodeConstants,
    IllegalArgumentException,
    ServiceException,
)
from framework.common.utils import JsonUtils
from framework.starter_di.public import (
    DiDependency,
)
from framework.starter_security.public import (
    SecurityContext,
    SecurityErrorCodes,
    SecurityException,
    SecurityRealm,
)
from framework.starter_tenant.public import (
    TenantSettings,
)
from framework.starter_web.public import (
    HttpUtils,
    Result,
    RoutePolicy,
)
from module_system.api.oauth2.dto.oauth2_client_dto import OAuth2ClientDTO
from module_system.controller.admin.oauth2.vo.open.open_access_token_resp_vo import (
    OAuth2OpenAccessTokenRespVO,
)
from module_system.controller.admin.oauth2.vo.open.open_authorize_info_req_vo import (
    OAuth2AuthorizeInfoReqVO,
)
from module_system.controller.admin.oauth2.vo.open.open_authorize_req_vo import OAuth2AuthorizeReqVO
from module_system.controller.admin.oauth2.vo.open.open_check_token_resp_vo import (
    OAuth2OpenCheckTokenRespVO,
)
from module_system.controller.admin.oauth2.vo.open.open_token_query_req_vo import (
    OAuth2TokenQueryReqVO,
)
from module_system.controller.admin.oauth2.vo.open.open_token_req_vo import OAuth2TokenReqVO
from module_system.convert.oauth2.oauth2_open_convert import OAuth2OpenConvert
from module_system.dal.dataobject.oauth2.oauth2_access_token_do import OAuth2AccessTokenDO
from module_system.definitions.enums.oauth2.oauth2_grant_type_enum import OAuth2GrantTypeEnum
from module_system.service.auth.system_workload_service import SystemWorkloadService
from module_system.service.oauth2.oauth2_approve_service import OAuth2ApproveService
from module_system.service.oauth2.oauth2_client_service import OAuth2ClientService
from module_system.service.oauth2.oauth2_grant_service import OAuth2GrantService
from module_system.service.oauth2.oauth2_token_service import OAuth2TokenService
from module_system.util.oauth2.oauth2_utils import OAuth2Utils

oauth2_open_controller = APIRouter(prefix="/oauth2/open", tags=["System - OAuth2 开放接口"])


class Oauth2OpenController:
    @staticmethod
    @oauth2_open_controller.post(
        "/token",
        summary="获得访问令牌",
        description="适合 code 授权码模式，或者 implicit 简化模式；在 sso.vue 单点登录界面被【获取】调用",
    )
    @RoutePolicy.public()
    async def post_access_token(
        request: Request,
        token_req: Annotated[OAuth2TokenReqVO, Form()],
        oauth2_grant_service: OAuth2GrantService = Depends(DiDependency(OAuth2GrantService)),
        oauth2_client_service: OAuth2ClientService = Depends(DiDependency(OAuth2ClientService)),
        oauth2_utils: OAuth2Utils = Depends(DiDependency(OAuth2Utils)),
        date_utils: DateUtils = Depends(DiDependency(DateUtils)),
        workloads: SystemWorkloadService = Depends(DiDependency(SystemWorkloadService)),
        tenant_settings: TenantSettings = Depends(DiDependency(TenantSettings)),
    ) -> Result[OAuth2OpenAccessTokenRespVO]:
        async with workloads.scope("system.auth", tenant_settings.default_tenant_id):
            scopes = await oauth2_utils.build_scopes(token_req.scope)
            grant_type_enum = OAuth2GrantTypeEnum.get_by_grant_type(token_req.grant_type)
            if not grant_type_enum:
                raise ServiceException(
                    GlobalErrorCodeConstants.BAD_REQUEST,
                    msg=f"未知授权类型({token_req.grant_type})",
                )
            if grant_type_enum is OAuth2GrantTypeEnum.IMPLICIT:
                raise ServiceException(
                    GlobalErrorCodeConstants.BAD_REQUEST, msg="Token 接口不支持 implicit 授权模式"
                )
            credentials = HttpUtils.obtain_basic_authorization(request)
            if credentials is None:
                raise SecurityException(SecurityErrorCodes.INVALID)
            client_id, client_secret = credentials
            client_do: OAuth2ClientDTO = await oauth2_client_service.validate_client(
                client_id, client_secret, token_req.grant_type, scopes, token_req.redirect_uri
            )
            access_token: OAuth2AccessTokenDO
            if grant_type_enum == OAuth2GrantTypeEnum.AUTHORIZATION_CODE:
                access_token = await oauth2_grant_service.grant_authorization_code_for_access_token(
                    client_do.client_id, token_req.code, token_req.redirect_uri, token_req.state
                )
            elif grant_type_enum == OAuth2GrantTypeEnum.PASSWORD:
                user_type = UserTypeEnum.ADMIN.code
                access_token = await oauth2_grant_service.grant_password(
                    token_req.username, token_req.password, client_do.client_id, scopes, user_type
                )
            elif grant_type_enum == OAuth2GrantTypeEnum.CLIENT_CREDENTIALS:
                access_token = await oauth2_grant_service.grant_client_credentials(
                    client_do.client_id, scopes
                )
            elif grant_type_enum == OAuth2GrantTypeEnum.REFRESH_TOKEN:
                access_token = await oauth2_grant_service.grant_refresh_token(
                    token_req.refresh_token, client_do.client_id
                )
            else:
                raise IllegalArgumentException(msg=f"未知授权类型: {token_req.grant_type}")
            if not access_token:
                raise IllegalArgumentException(msg="访问令牌不能为空!")
            return Result.success(data=OAuth2OpenConvert.convert(access_token, date_utils))

    @staticmethod
    @oauth2_open_controller.delete(
        "/token", summary="删除访问令牌", description="删除指定的访问令牌"
    )
    @RoutePolicy.public()
    async def revoke_token(
        request: Request,
        req_vo: OAuth2TokenQueryReqVO = Query(),
        oauth2_grant_service: OAuth2GrantService = Depends(DiDependency(OAuth2GrantService)),
        oauth2_client_service: OAuth2ClientService = Depends(DiDependency(OAuth2ClientService)),
        workloads: SystemWorkloadService = Depends(DiDependency(SystemWorkloadService)),
        tenant_settings: TenantSettings = Depends(DiDependency(TenantSettings)),
    ) -> Result[bool]:
        token = req_vo.token
        async with workloads.scope("system.auth", tenant_settings.default_tenant_id):
            credentials = HttpUtils.obtain_basic_authorization(request)
            if credentials is None:
                raise SecurityException(SecurityErrorCodes.INVALID)
            client_id, client_secret = credentials
            client_do: OAuth2ClientDTO = await oauth2_client_service.validate_client(
                client_id, client_secret, None, None, None
            )
            result = await oauth2_grant_service.revoke_token(client_do.client_id, token)
            return Result.success(data=result)

    @staticmethod
    @oauth2_open_controller.post(
        "/check-token", summary="校验访问令牌", description="校验指定的访问令牌是否有效"
    )
    @RoutePolicy.public()
    async def check_token(
        request: Request,
        req_vo: OAuth2TokenQueryReqVO = Query(),
        oauth2_token_service: OAuth2TokenService = Depends(DiDependency(OAuth2TokenService)),
        oauth2_client_service: OAuth2ClientService = Depends(DiDependency(OAuth2ClientService)),
        date_utils: DateUtils = Depends(DiDependency(DateUtils)),
        workloads: SystemWorkloadService = Depends(DiDependency(SystemWorkloadService)),
        tenant_settings: TenantSettings = Depends(DiDependency(TenantSettings)),
    ) -> Result[OAuth2OpenCheckTokenRespVO]:
        token = req_vo.token
        async with workloads.scope("system.auth", tenant_settings.default_tenant_id):
            credentials = HttpUtils.obtain_basic_authorization(request)
            if credentials is None:
                raise SecurityException(SecurityErrorCodes.INVALID)
            client_id, client_secret = credentials
            await oauth2_client_service.validate_client(client_id, client_secret)
            access_token = await oauth2_token_service.check_access_token(token)
            if access_token.client_id != client_id:
                raise SecurityException(SecurityErrorCodes.DENIED, detail="访问令牌与客户端不匹配")
            if not access_token:
                raise IllegalArgumentException(msg="访问令牌不能为空")
            return Result.success(data=OAuth2OpenConvert.convert2(access_token, token))

    @staticmethod
    @oauth2_open_controller.get(
        "/authorize",
        summary="获得授权信息",
        description="适合 code 授权码模式，或者 implicit 简化模式；在 sso.vue 单点登录界面被【获取】调用",
    )
    @RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT)
    async def authorize(
        req_vo: OAuth2AuthorizeInfoReqVO = Query(),
        oauth2_client_service: OAuth2ClientService = Depends(DiDependency(OAuth2ClientService)),
        oauth2_approve_service: OAuth2ApproveService = Depends(DiDependency(OAuth2ApproveService)),
        security: SecurityContext = Depends(DiDependency(SecurityContext)),
    ) -> Result:
        client_id = req_vo.client_id
        client_dto: OAuth2ClientDTO = await oauth2_client_service.validate_client(client_id)
        approves = await oauth2_approve_service.get_approve_list(
            int(security.require().account_id), UserTypeEnum.ADMIN.code, client_id
        )
        return Result.success(data=OAuth2OpenConvert.convert_oauth_info(client_dto, approves))

    @staticmethod
    @oauth2_open_controller.post(
        "/authorize",
        summary="申请授权",
        description="适合 code 授权码模式，或者 implicit 简化模式；在 sso.vue 单点登录界面被【提交】调用",
    )
    @RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT)
    async def approve_or_deny(
        req_vo: OAuth2AuthorizeReqVO = Query(),
        oauth2_grant_service: OAuth2GrantService = Depends(DiDependency(OAuth2GrantService)),
        oauth2_client_service: OAuth2ClientService = Depends(DiDependency(OAuth2ClientService)),
        oauth2_approve_service: OAuth2ApproveService = Depends(DiDependency(OAuth2ApproveService)),
        oauth2_utils: OAuth2Utils = Depends(DiDependency(OAuth2Utils)),
        security: SecurityContext = Depends(DiDependency(SecurityContext)),
    ) -> Result[str | None]:
        redirect_uri = req_vo.redirect_uri
        auto_approve = req_vo.auto_approve
        response_type = req_vo.response_type
        client_id = req_vo.client_id
        scope = req_vo.scope
        state = req_vo.state
        user_type = UserTypeEnum.ADMIN.code
        scopes = JsonUtils.parse_obj(scope, dict) if scope else {}
        login_user_id = int(security.require().account_id)
        grant_type_enum = OAuth2GrantTypeEnum.get_grant_type_enum(response_type)
        if not grant_type_enum:
            raise ServiceException(
                GlobalErrorCodeConstants.BAD_REQUEST, msg=f"未知授权类型({response_type})"
            )
        client_do = await oauth2_client_service.validate_client(
            client_id, None, grant_type_enum.code, scopes.keys(), redirect_uri
        )
        if auto_approve:
            if not await oauth2_approve_service.check_for_pre_approval(
                login_user_id, user_type, client_id, scopes.keys()
            ):
                return Result.success(data=None)
        elif not await oauth2_approve_service.update_after_approval(
            login_user_id, user_type, client_id, scopes
        ):
            return Result.success(
                data=await oauth2_utils.build_unsuccessful_redirect(
                    redirect_uri, response_type, state, "access_denied", "User denied access"
                )
            )
        approve_scopes = [scope for scope, approved in scopes.items() if approved]
        if grant_type_enum == OAuth2GrantTypeEnum.AUTHORIZATION_CODE:
            authorization_code = await oauth2_grant_service.grant_authorization_code_for_code(
                login_user_id, user_type, client_do.client_id, approve_scopes, redirect_uri, state
            )
            return Result.success(
                data=await oauth2_utils.build_authorization_code_redirect_uri(
                    redirect_uri, authorization_code, state
                )
            )
        access_token = await oauth2_grant_service.grant_implicit(
            login_user_id, user_type, client_do.client_id, approve_scopes
        )
        return Result.success(
            data=await oauth2_utils.build_implicit_redirect_uri(
                redirect_uri,
                access_token.access_token,
                state,
                access_token.expires_time,
                approve_scopes,
                client_do.additional_information,
            )
        )
