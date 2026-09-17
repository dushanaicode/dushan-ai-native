from __future__ import annotations

from typing import Any

from pydantic import Field, HttpUrl, field_validator

from framework.common.validator.not_empty import NotEmpty
from framework.common.validator.url import URL
from module_infra.framework.file.core.client.file_client_config import FileClientConfig


class LocalFileClientConfig(FileClientConfig):
    """
    本地文件客户端的配置类
    """

    base_path: str = Field(..., description="基础路径")
    domain: HttpUrl = Field(..., description="自定义域名")

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
