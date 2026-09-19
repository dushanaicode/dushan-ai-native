from __future__ import annotations

from typing import Any

from pydantic import Field, HttpUrl, field_validator

from framework.common.validator import URL, NotEmpty
from module_infra.framework.file.core.client.file_client_config import FileClientConfig


class SftpFileClientConfig(FileClientConfig):
    """Sftp 文件客户端的配置类"""

    base_path: str = Field(..., description="基础路径")
    domain: HttpUrl = Field(..., description="自定义域名")
    host: str = Field(..., description="主机地址")
    port: int = Field(..., description="主机端口", strict=True, ge=1, le=65535)
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")
    known_hosts: str = Field(
        ..., min_length=1, description="SSH known_hosts 路径或内容，为安全连接所必需，生产环境必填"
    )

    @field_validator("base_path", mode="before")
    @classmethod
    def _validate_base_path(cls, v: Any) -> Any:
        NotEmpty.require_not_empty(field_name="base_path", value=v, error_msg="基础路径不能为空")
        return v

    @field_validator("domain", mode="before")
    @classmethod
    def _validate_domain(cls, v: Any) -> Any:
        NotEmpty.require_not_empty(field_name="domain", value=v, error_msg="domain 不能为空")
        URL.require_url(field_name="domain", value=v, error_msg="domain 必须是 URL 格式")
        return v

    @field_validator("host", mode="before")
    @classmethod
    def _validate_host(cls, v: Any) -> Any:
        NotEmpty.require_not_empty(field_name="host", value=v, error_msg="host 不能为空")
        return v

    @field_validator("username", mode="before")
    @classmethod
    def _validate_username(cls, v: Any) -> Any:
        NotEmpty.require_not_empty(field_name="username", value=v, error_msg="用户名不能为空")
        return v

    @field_validator("password", mode="before")
    @classmethod
    def _validate_password(cls, v: Any) -> Any:
        NotEmpty.require_not_empty(field_name="password", value=v, error_msg="密码不能为空")
        return v
