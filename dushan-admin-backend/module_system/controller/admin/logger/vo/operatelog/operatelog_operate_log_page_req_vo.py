from datetime import datetime
from typing import Annotated

from pydantic import Field

from framework.common.contracts import (
    SnowflakeReferenceInput,
)
from framework.common.page import PageQuery


class OperateLogPageReqVO(PageQuery):
    """管理后台 - 操作日志分页列表 Request VO"""

    user_id: Annotated[SnowflakeReferenceInput | None, Field(None, description="用户编号")]
    biz_id: Annotated[SnowflakeReferenceInput | None, Field(None, description="操作模块业务编号")]
    type: Annotated[str | None, Field(None, description="操作模块，模拟匹配")]
    sub_type: Annotated[str | None, Field(None, description="操作名，模拟匹配")]
    action: Annotated[str | None, Field(None, description="操作明细，模拟匹配")]
    create_time: Annotated[
        list[datetime] | None, Field(None, exclude=True, description="创建时间范围")
    ]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "userId": 1024,
                    "bizId": 1,
                    "type": "订单",
                    "subType": "创建订单",
                    "action": "修改编号为 1 的用户信息",
                    "createTime": ["2020-05-20T05:20:00Z", "2022-07-01T23:59:59Z"],
                    "pageNo": 1,
                    "pageSize": 10,
                }
            ]
        }
    }
