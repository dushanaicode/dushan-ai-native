from typing import Annotated

from pydantic import Field, field_validator

from framework.common.contracts import (
    SnowflakeIdInput,
)
from framework.common.schemas import BaseRequestVO
from module_infra.framework.file.core.client.abstract_file_client import AbstractFileClient


class FileCreateDirectoryReqVO(BaseRequestVO):
    """管理后台 - 文件管理 新建目录请求 VO"""

    config_id: Annotated[SnowflakeIdInput, Field(..., description="存储配置 ID")]
    directory_path: Annotated[str, Field(..., description="目录路径，如 images/avatars/")]

    @field_validator("directory_path")
    @classmethod
    def validate_directory_path(cls, value: str) -> str:
        return AbstractFileClient.key(value)
