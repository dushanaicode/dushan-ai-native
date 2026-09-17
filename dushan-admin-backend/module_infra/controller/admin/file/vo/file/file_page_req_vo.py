from datetime import datetime
from typing import Annotated

from pydantic import Field

from framework.common.contracts.snowflake_id import (
    SnowflakeIdInput,
)
from framework.common.page.schemas.page_query import PageQuery


class FilePageReqVO(PageQuery):
    """管理后台 - 文件分页列表 Request VO"""

    path: Annotated[str | None, Field(default=None, description="文件路径，模糊匹配")]
    file_type: Annotated[
        str | None, Field(default=None, alias="type", description="文件类型，模糊匹配")
    ]
    config_id: Annotated[SnowflakeIdInput | None, Field(default=None, description="文件配置ID")]
    create_time: Annotated[
        list[datetime] | None, Field(None, exclude=True, description="创建时间范围 [开始, 结束]")
    ]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "path": "dushan",
                    "type": "jpg",
                    "configId": 1,
                    "createTime": ["2020-05-02 05:20:00", "2020-05-02 13:14:00"],
                }
            ]
        }
    }
