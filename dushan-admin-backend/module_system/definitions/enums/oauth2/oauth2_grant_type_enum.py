from framework.common.enums.base_enum import BaseEnum
from framework.common.exception.constants.global_error_code_constants import (
    GlobalErrorCodeConstants,
)
from framework.common.exception.exceptions.server_exception import ServerException


class OAuth2GrantTypeEnum(BaseEnum):
    PASSWORD = ("password", "密码模式")
    AUTHORIZATION_CODE = ("authorization_code", "授权码模式")
    IMPLICIT = ("implicit", "简化模式")
    CLIENT_CREDENTIALS = ("client_credentials", "客户端模式")
    REFRESH_TOKEN = ("refresh_token", "刷新模式")

    @classmethod
    def get_by_grant_type(cls, grant_type: str) -> "OAuth2GrantTypeEnum | None":
        """根据 grant_type 返回对应的枚举项，如果没有匹配的，返回 None"""
        for item in cls:
            if item.code == grant_type:
                return item
        return None

    @classmethod
    def get_grant_type_enum(cls, response_type: str) -> "OAuth2GrantTypeEnum | None":
        """
        根据 response_type 返回对应的 OAuth2GrantTypeEnum 枚举
        :param response_type: 授权类型参数值，可能的值为 'code' 或 'token'
        :return: OAuth2GrantTypeEnum 枚举
        """
        if response_type == "code":
            return OAuth2GrantTypeEnum.AUTHORIZATION_CODE
        elif response_type == "token":
            return OAuth2GrantTypeEnum.IMPLICIT
        else:
            raise ServerException(
                GlobalErrorCodeConstants.BAD_REQUEST,
                msg="response_type 参数值只允许 'code' 和 'token'",
            )
