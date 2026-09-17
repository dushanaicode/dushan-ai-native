from datetime import datetime
from typing import Annotated

from pydantic import Field

from framework.common.page.schemas.page_query import PageQuery


class LoginLogPageReqVO(PageQuery):
    """管理后台 - 登录日志分页列表 Request VO"""

    user_ip: Annotated[str | None, Field(None, description="用户 IP，模拟匹配")]
    username: Annotated[str | None, Field(None, description="用户账号，模拟匹配")]
    result: Annotated[int | None, Field(None, description="操作状态")]
    log_type: Annotated[int | None, Field(None, description="日志类型")]
    create_time: Annotated[
        list[datetime] | None, Field(None, exclude=True, description="创建时间范围")
    ]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "userIp": "127.0.0.1",
                    "username": "渡山",
                    "result": 0,
                    "logType": 0,
                    "createTime": ["2020-05-20T05:20:00Z", "2022-07-01T23:59:59Z"],
                    "pageNo": 1,
                    "pageSize": 10,
                }
            ]
        }
    }
