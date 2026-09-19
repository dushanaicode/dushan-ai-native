from datetime import datetime
from typing import Annotated

from pydantic import Field

from framework.common.contracts import (
    SnowflakeIdStr,
)
from framework.common.schemas import BaseVO


class SocialUserRespVO(BaseVO):
    """管理后台 - 社交用户信息 Response VO"""

    id: Annotated[SnowflakeIdStr | None, Field(None, description="主键(自增策略)")]
    type: Annotated[int, Field(..., description="社交平台的类型")]
    openid: Annotated[str, Field(..., description="社交 openid")]
    token: Annotated[str | None, Field(None, description="社交 token", exclude=True)]
    raw_token_info: Annotated[
        str, Field(..., description="原始 Token 数据，一般是 JSON 格式", exclude=True)
    ]
    nickname: Annotated[str, Field(..., description="用户昵称")]
    avatar: Annotated[str | None, Field(None, description="用户头像")]
    raw_user_info: Annotated[
        str, Field(..., description="原始用户数据，一般是 JSON 格式", exclude=True)
    ]
    code: Annotated[str, Field(..., description="最后一次的认证 code", exclude=True)]
    state: Annotated[str | None, Field(None, description="最后一次的认证 state", exclude=True)]
    create_time: Annotated[datetime, Field(..., description="创建时间")]
    update_time: Annotated[datetime, Field(..., description="更新时间")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 14569,
                    "type": 30,
                    "openid": "666",
                    "token": "666",
                    "rawTokenInfo": "{}",
                    "nickname": "渡山",
                    "avatar": "https://www.dushan.info/xxx.png",
                    "rawUserInfo": "{}",
                    "code": "666666",
                    "state": "123456",
                    "createTime": "2020-05-20T05:20:00Z",
                    "updateTime": "2020-05-20T05:20:00Z",
                }
            ]
        }
    }
