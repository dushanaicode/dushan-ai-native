from typing import Annotated

from pydantic import Field

from framework.common.contracts import (
    SnowflakeIdInput,
)
from framework.common.page import PageQuery


class FileSearchReqVO(PageQuery):
    """管理后台 - 文件管理 搜索请求 VO"""

    config_id: Annotated[SnowflakeIdInput, Field(..., description="存储配置 ID")]
    keyword: Annotated[str, Field(default="", description="搜索关键词")]
    search_mode: Annotated[
        str, Field(default="fuzzy", description="搜索模式: fuzzy(模糊) / prefix(前缀)")
    ]
    prefix: Annotated[str, Field(default="", description="搜索范围（目录前缀）")]
