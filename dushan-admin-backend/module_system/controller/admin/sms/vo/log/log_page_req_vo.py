from datetime import datetime
from typing import Annotated

from pydantic import Field

from framework.common.contracts import (
    SnowflakeIdInput,
)
from framework.common.page import PageQuery


class SmsLogPageReqVO(PageQuery):
    """管理后台 - 短信日志分页列表 Request VO"""

    channel_id: Annotated[SnowflakeIdInput | None, Field(None, description="短信渠道编号")]
    template_id: Annotated[SnowflakeIdInput | None, Field(None, description="模板编号")]
    mobile: Annotated[str | None, Field(None, description="手机号")]
    send_status: Annotated[
        int | None, Field(None, description="发送状态，参见 SmsSendStatusEnum 枚举类")
    ]
    send_time: Annotated[list[datetime] | None, Field(None, description="发送时间")]
    receive_status: Annotated[
        int | None, Field(None, description="接收状态，参见 SmsReceiveStatusEnum 枚举类")
    ]
    receive_time: Annotated[list[datetime] | None, Field(None, description="接收时间")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "channelId": 10,
                    "templateId": 20,
                    "mobile": "18888888888",
                    "sendStatus": 1,
                    "sendTime": ["2024-01-01 12:00:00", "2024-01-02 12:00:00"],
                    "receiveStatus": 0,
                    "receiveTime": ["2024-01-01 12:00:00", "2024-01-02 12:00:00"],
                    "pageNo": 1,
                    "pageSize": 10,
                }
            ]
        }
    }
