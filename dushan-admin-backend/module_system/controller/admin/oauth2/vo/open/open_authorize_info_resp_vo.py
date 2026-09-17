from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.schemas.base_vo import BaseVO
from framework.common.validator.not_null import NotNull
from module_system.controller.admin.oauth2.vo.open.client import Client
from module_system.controller.admin.oauth2.vo.open.scope_key_value import ScopeKeyValue


class OAuth2OpenAuthorizeInfoRespVO(BaseVO):
    """管理后台 - 授权页信息 Response VO"""

    client: Annotated[Client, Field(..., description="客户端信息")]
    scopes: Annotated[
        list[ScopeKeyValue],
        Field(
            ...,
            description="scope 的选中信息，使用 List 保证有序性，Key 是 scope，Value 为是否选中",
        ),
    ]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "client": {"name": "渡山", "logo": "https://www.dushan.info/xx.png"},
                    "scopes": [{"key": "read_write", "value": "读写权限"}],
                }
            ]
        }
    }

    @field_validator("client", mode="before")
    @classmethod
    def _validate_client(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="client", value=v, error_msg="客户端信息不能为空")
        return v

    @field_validator("scopes", mode="before")
    @classmethod
    def _validate_scopes(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="scopes", value=v, error_msg="scope 的选中信息不能为空")
        return v
