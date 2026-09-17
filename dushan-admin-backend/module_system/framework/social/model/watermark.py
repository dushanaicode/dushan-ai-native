from framework.common.schemas.base_vo import BaseVO


class Watermark(BaseVO):
    """承载微信小程序手机号解密结果中的水印信息。"""

    timestamp: int
    appid: str
