from typing import Annotated

from pydantic import Field

from framework.common.contracts import (
    SnowflakeIdInput,
)
from framework.common.schemas import BaseRequestVO


class FileDeleteByKeysReqVO(BaseRequestVO):
    """管理后台 - 文件管理 批量通过存储key删除文件请求 VO"""

    config_id: Annotated[SnowflakeIdInput, Field(..., description="存储配置 ID")]
    keys: Annotated[str, Field(..., description="文件存储路径列表(逗号分隔)")]
