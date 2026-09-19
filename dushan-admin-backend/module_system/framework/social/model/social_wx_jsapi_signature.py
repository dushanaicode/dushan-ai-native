from framework.common.schemas import BaseVO


class SocialWxJsapiSignature(BaseVO):
    """微信公众号JSAPI签名模型"""

    app_id: str
    nonce_str: str
    timestamp: int
    url: str
    signature: str

    @classmethod
    def from_dict(cls, data: dict):
        """从字典数据生成 SocialWxJsapiSignature 实例"""
        return cls(**data)
