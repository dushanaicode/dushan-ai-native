from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.contracts import (
    SnowflakeIdInput,
)
from framework.common.schemas import BaseRequestVO
from framework.common.validator import Email, NotNull


class MailAccountSaveReqVO(BaseRequestVO):
    """管理后台 - 邮箱账号创建/修改 Request VO"""

    id: Annotated[SnowflakeIdInput | None, Field(None, description="编号")]
    mail: Annotated[str, Field(..., description="邮箱")]
    username: Annotated[str, Field(..., description="用户名")]
    password: Annotated[str, Field(..., description="密码")]
    host: Annotated[str, Field(..., description="SMTP 服务器域名")]
    port: Annotated[int, Field(..., description="SMTP 服务器端口")]
    ssl_enable: Annotated[bool, Field(..., description="是否开启 ssl")]
    starttls_enable: Annotated[bool, Field(..., description="是否开启 starttls")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1024,
                    "mail": "729227973@qq.com",
                    "username": "dushan",
                    "password": "123456",
                    "host": "www.dushan.info",
                    "port": 80,
                    "sslEnable": True,
                    "starttlsEnable": True,
                }
            ]
        }
    }

    @field_validator("mail", mode="before")
    @classmethod
    def _validate_mail(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="mail", value=v, error_msg="邮箱不能为空")
        Email.require_email(field_name="mail", value=v, error_msg="必须是 Email 格式")
        return v

    @field_validator("username", mode="before")
    @classmethod
    def _validate_username(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="username", value=v, error_msg="用户名不能为空")
        return v

    @field_validator("password", mode="before")
    @classmethod
    def _validate_password(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="password", value=v, error_msg="密码必填")
        return v

    @field_validator("host", mode="before")
    @classmethod
    def _validate_host(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="host", value=v, error_msg="SMTP 服务器域名不能为空")
        return v

    @field_validator("port", mode="before")
    @classmethod
    def _validate_port(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="port", value=v, error_msg="SMTP 服务器端口不能为空")
        return v

    @field_validator("ssl_enable", mode="before")
    @classmethod
    def _validate_ssl_enable(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="ssl_enable", value=v, error_msg="是否开启 ssl 必填")
        return v

    @field_validator("starttls_enable", mode="before")
    @classmethod
    def _validate_starttls_enable(cls, v: Any) -> Any:
        NotNull.require_not_null(
            field_name="starttls_enable", value=v, error_msg="是否开启 starttls 必填"
        )
        return v
