from framework.common.schemas.base_vo import BaseVO
from module_system.framework.social.model.watermark import Watermark


class SocialWxMaPhoneNumberInfo(BaseVO):
    """微信小程序手机号信息模型"""

    phone_number: str
    pure_phone_number: str
    country_code: str
    watermark: Watermark

    @classmethod
    def from_json(cls, json: str):
        """从 JSON 字符串生成 SocialWxMaPhoneNumberInfo 实例"""
        return cls.model_validate_json(json)
