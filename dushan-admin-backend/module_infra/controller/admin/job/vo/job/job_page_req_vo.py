from datetime import datetime
from typing import Annotated

from pydantic import Field

from framework.common.page import PageQuery


class JobPageReqVO(PageQuery):
    """管理后台 - 定时任务分页列表 Request VO"""

    name: Annotated[str | None, Field(default=None, description="任务名称，模糊匹配")]
    status: Annotated[
        int | None, Field(default=None, description="任务状态，参见 JobStatusEnum 枚举")
    ]
    handler_name: Annotated[str | None, Field(default=None, description="处理器的名字，模糊匹配")]
    create_time: Annotated[
        list[datetime] | None, Field(default=None, exclude=True, description="创建时间范围")
    ]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "测试任务",
                    "status": 0,
                    "handlerName": "sysUserSessionTimeoutJob",
                    "createTime": ["2020-05-20T05:20:00Z", "2022-07-01T23:59:59Z"],
                }
            ]
        }
    }
