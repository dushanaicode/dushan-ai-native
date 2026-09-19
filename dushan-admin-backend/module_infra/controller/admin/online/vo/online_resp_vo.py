from datetime import datetime
from typing import Annotated

from pydantic import Field

from framework.common.schemas import BaseVO


class OnlineInfoRespVO(BaseVO):
    """管理后台 - 在线用户信息 Response VO"""

    token_id: Annotated[str | None, Field(default=None, description="会话编号")]
    user_name: Annotated[str | None, Field(default=None, description="登录名称")]
    dept_name: Annotated[str | None, Field(default=None, description="所属部门")]
    ipaddr: Annotated[str | None, Field(default=None, description="主机")]
    login_location: Annotated[str | None, Field(default=None, description="登录地点")]
    browser: Annotated[str | None, Field(default=None, description="浏览器类型")]
    os: Annotated[str | None, Field(default=None, description="操作系统")]
    login_time: Annotated[datetime | None, Field(default=None, description="登录时间")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "tokenId": "abc123",
                    "userName": "admin",
                    "deptName": "研发部",
                    "ipaddr": "192.168.1.1",
                    "loginLocation": "内网IP",
                    "browser": "Chrome",
                    "os": "Windows 10",
                    "loginTime": "2020-05-20T05:20:00Z",
                }
            ]
        }
    }
