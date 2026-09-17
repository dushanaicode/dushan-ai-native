from datetime import datetime
from typing import Annotated

from pydantic import Field

from framework.common.contracts.snowflake_id import (
    SnowflakeIdStr,
)
from framework.common.schemas.base_vo import BaseVO


class ProfileOnlineDeviceVO(BaseVO):
    """管理后台 - 用户在线设备信息 VO"""

    token_id: Annotated[SnowflakeIdStr, Field(..., description="会话记录编号")]
    device_name: Annotated[
        str | None, Field(default=None, description="设备名称 (例如: Chrome 浏览器)")
    ]
    ip_address: Annotated[str | None, Field(default=None, description="IP 地址")]
    login_location: Annotated[str | None, Field(default=None, description="登录地点")]
    browser: Annotated[str | None, Field(default=None, description="浏览器")]
    os: Annotated[str | None, Field(default=None, description="操作系统")]
    login_time: Annotated[datetime | None, Field(default=None, description="登录时间")]
    online: Annotated[bool, Field(..., description="是否在线")]
    is_current: Annotated[bool, Field(..., description="是否为当前设备")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "tokenId": "abc123xyz456",
                    "deviceName": "Chrome 浏览器",
                    "ipAddress": "192.168.1.1",
                    "loginLocation": "内网IP",
                    "browser": "Chrome 131.0.0.0",
                    "os": "Windows 10",
                    "loginTime": "2024-07-28T12:00:00Z",
                    "online": True,
                    "isCurrent": True,
                }
            ]
        }
    }
