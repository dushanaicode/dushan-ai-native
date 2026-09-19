from typing import Annotated

from pydantic import Field

from framework.common.contracts import (
    SnowflakeIdInput,
)
from framework.common.schemas import BaseRequestVO


class FileListObjectsReqVO(BaseRequestVO):
    """管理后台 - 文件管理 列举对象请求 VO"""

    config_id: Annotated[SnowflakeIdInput, Field(..., description="存储配置 ID")]
    prefix: Annotated[str, Field(default="", description="目录前缀")]
    delimiter: Annotated[str, Field(default="/", description="分隔符")]
