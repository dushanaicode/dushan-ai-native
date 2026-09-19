from pydantic import Field

from framework.common.schemas import BaseDTO


class SmsChannelProperties(BaseDTO):
    """短信渠道配置类"""

    id: int | None = Field(None, description="短信渠道 ID (实际渠道应有值)")
    signature: str | None = Field(None, description="短信签名 (实际渠道应有值)")
    code: str = Field(..., description="渠道编码, 参见 SmsChannelEnum")
    api_key: str = Field(..., description="短信 API 的账号")
    api_secret: str = Field(..., description="短信 API 的密钥")
    callback_url: str | None = Field(None, description="短信发送回调 URL")
