from pydantic import Field

from framework.common.contracts.snowflake_id import (
    SnowflakeIdInput,
)
from framework.common.schemas.base_request_vo import BaseRequestVO


class FileRenameReqVO(BaseRequestVO):
    """管理后台 - 文件重命名 Request VO"""

    config_id: SnowflakeIdInput = Field(..., description="存储配置ID")
    old_key: str = Field(..., description="原始文件/目录的存储key")
    new_name: str = Field(..., description="新名称")
