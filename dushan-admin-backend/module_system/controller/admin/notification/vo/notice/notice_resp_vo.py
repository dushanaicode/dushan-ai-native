from datetime import datetime
from typing import Annotated

from pydantic import Field

from framework.common.contracts import (
    SnowflakeIdStr,
)
from framework.common.schemas import BaseVO


class NoticeRespVO(BaseVO):
    """管理后台 - 通知信息 Response VO"""

    id: Annotated[SnowflakeIdStr, Field(..., description="通知序号")]
    code: Annotated[str | None, Field(None, description="通知编码")]
    builtin: Annotated[int | None, Field(None, description="内置类型，参见 BuiltinTypeEnum")]
    title: Annotated[str, Field(..., description="通知标题")]
    type: Annotated[int, Field(..., description="通知类型")]
    user_type: Annotated[int, Field(..., description="用户类型")]
    content: Annotated[str, Field(..., description="通知内容")]
    channels: Annotated[list[str], Field(..., description="通知渠道")]
    sms_template_code: Annotated[str | None, Field(None, description="短信模板编码")]
    mail_account_id: Annotated[SnowflakeIdStr | None, Field(None, description="邮箱账号编号")]
    publisher: Annotated[str, Field(..., description="发布人")]
    status: Annotated[int, Field(..., description="状态，参见 StatusEnum 枚举类")]
    create_time: Annotated[datetime, Field(..., description="创建时间")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1024,
                    "code": "AI_TASK_NOTICE",
                    "title": "小博主",
                    "type": 1,
                    "userType": 1,
                    "channels": ["INTERNAL", "SMS"],
                    "content": "渡山",
                    "publisher": "渡山源码",
                    "status": 1,
                    "createTime": "2020-05-20T05:20:00Z",
                }
            ]
        }
    }
