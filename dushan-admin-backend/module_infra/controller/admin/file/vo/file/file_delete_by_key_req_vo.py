from typing import Annotated

from pydantic import Field

from framework.common.contracts.snowflake_id import (
    SnowflakeIdInput,
)
from framework.common.schemas.base_request_vo import BaseRequestVO


class FileDeleteByKeyReqVO(BaseRequestVO):
    """管理后台 - 文件管理 通过存储key删除文件请求 VO"""

    config_id: Annotated[SnowflakeIdInput, Field(..., description="存储配置 ID")]
    key: Annotated[str, Field(..., description="文件存储路径(key)")]
