from framework.common.schemas.base_vo import BaseVO


class SocialTemplateInfo(BaseVO):
    """模板信息模型"""

    pri_tmpl_id: str
    title: str
    content: str
    example: str | None = None
    type: int

    @classmethod
    def from_json(cls, json: str):
        """从 JSON 字符串生成 SocialTemplateInfo 实例"""
        return cls.model_validate_json(json)
