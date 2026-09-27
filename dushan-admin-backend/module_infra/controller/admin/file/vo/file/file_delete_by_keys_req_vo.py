from typing import Annotated

from pydantic import Field

from framework.common.contracts import (
    SnowflakeIdInput,
)
from framework.common.schemas import BaseRequestVO


class FileDeleteByKeysReqVO(BaseRequestVO):
    """管理后台 - 文件管理 批量通过存储key删除文件请求 VO"""

    config_id: Annotated[SnowflakeIdInput, Field(..., description="存储配置 ID")]
    keys: Annotated[
        list[Annotated[str, Field(min_length=1)]],
        Field(..., min_length=1, description="文件存储路径数组，使用重复 Query 参数，保留原值"),
    ]
