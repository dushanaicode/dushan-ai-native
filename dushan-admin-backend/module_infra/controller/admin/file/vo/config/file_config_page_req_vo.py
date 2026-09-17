from datetime import datetime
from typing import Annotated

from pydantic import Field

from framework.common.page.schemas.page_query import PageQuery


class FileConfigPageReqVO(PageQuery):
    """管理后台 - 文件配置分页列表 Request VO"""

    name: Annotated[str | None, Field(default=None, description="配置名")]
    storage: Annotated[int | None, Field(default=None, description="存储器")]
    status: Annotated[int | None, Field(default=None, description="状态")]
    create_time: Annotated[
        list[datetime] | None, Field(None, exclude=True, description="创建时间范围")
    ]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "S3 - 阿里云",
                    "storage": 1,
                    "status": 0,
                    "createTime": ["2020-05-02 05:20:00", "2020-05-02 13:14:00"],
                }
            ]
        }
    }
