from datetime import datetime, timezone

from framework.common.dates import DateUtils
from module_system.api.oauth2.dto.oauth2_access_token_resp_dto import OAuth2AccessTokenRespDTO
from module_system.api.oauth2.dto.oauth2_client_dto import OAuth2ClientDTO
from module_system.controller.admin.oauth2.vo.open.client import Client
from module_system.controller.admin.oauth2.vo.open.open_access_token_resp_vo import (
    OAuth2OpenAccessTokenRespVO,
)
from module_system.controller.admin.oauth2.vo.open.open_authorize_info_resp_vo import (
    OAuth2OpenAuthorizeInfoRespVO,
)
from module_system.controller.admin.oauth2.vo.open.open_check_token_resp_vo import (
    OAuth2OpenCheckTokenRespVO,
)
from module_system.controller.admin.oauth2.vo.open.scope_key_value import ScopeKeyValue
from module_system.dal.dataobject.oauth2.oauth2_access_token_do import OAuth2AccessTokenDO
from module_system.dal.dataobject.oauth2.oauth2_approve_do import OAuth2ApproveDO


class OAuth2OpenConvert:
    @staticmethod
    def convert(
        oauth: OAuth2AccessTokenRespDTO, date_utils: DateUtils
    ) -> OAuth2OpenAccessTokenRespVO:
        """将 OAuth2AccessTokenDO 转换为 OAuth2OpenAccessTokenRespVO"""
        expires_in = max(
            0,
            int(
                (
                    oauth.expires_time - datetime.now(timezone.utc).replace(tzinfo=None)
                ).total_seconds()
            ),
        )
        scope = " ".join(oauth.scopes)
        return OAuth2OpenAccessTokenRespVO(
            access_token=oauth.access_token,
            refresh_token=oauth.refresh_token,
            token_type="Bearer",
            expires_in=expires_in,
            scope=scope,
        )

    @staticmethod
    def convert2(oauth: OAuth2AccessTokenDO, access_token: str) -> OAuth2OpenCheckTokenRespVO:
        """将 OAuth2AccessTokenDO 转换为 OAuth2OpenCheckTokenRespVO"""
        exp = int(oauth.expires_time.replace(tzinfo=timezone.utc).timestamp())
        return OAuth2OpenCheckTokenRespVO(
            user_id=oauth.user_id,
            user_type=oauth.user_type,
            tenant_id=oauth.tenant_id,
            client_id=oauth.client_id,
            scopes=oauth.scopes,
            access_token=access_token,
            exp=exp,
        )

    @staticmethod
    def convert_oauth_info(
        client: OAuth2ClientDTO, approves: list[OAuth2ApproveDO]
    ) -> OAuth2OpenAuthorizeInfoRespVO:
        """将 OAuth2ClientCacheDTO 和 OAuth2ApproveDO 列表转换为 OAuth2OpenAuthorizeInfoRespVO"""
        approve_map: dict[str, OAuth2ApproveDO] = {approve.scope: approve for approve in approves}
        scopes = [
            ScopeKeyValue(
                key=scope,
                value=str(
                    approve_map.get(scope, OAuth2ApproveDO(scope=scope, approved=False)).approved
                ),
            )
            for scope in client.scopes
        ]
        return OAuth2OpenAuthorizeInfoRespVO(
            client=Client(name=client.name, logo=client.logo), scopes=scopes
        )
