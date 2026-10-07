from typing import Any, ClassVar

from pydantic import Field

from framework.common.schemas import BaseBO


class SmsSendMessage(BaseBO):
    """
    短信发送消息的数据模型
    """

    message_id: str = Field(..., description="消息唯一ID")
    log_id: int = Field(..., description="短信日志编号")
    mobile: str = Field(..., description="手机号")
    channel_id: int = Field(..., description="短信渠道编号")
    api_template_id: str = Field(..., description="短信 API 的模板编号")
    template_params: dict[str, Any] = Field(
        default_factory=dict, description="短信模板参数 (字典形式)"
    )
    stream_key: ClassVar[str] = "sms:send"
