from pydantic import BaseModel, ConfigDict, field_validator

from framework.common.utils.validation.validation_utils import ValidationUtils


class BannerSettings(BaseModel):
    """声明启动展示开关，所有默认值仅从公共 YAML 读取。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    enabled: bool
    show_logo: bool
    show_worship: bool
    show_startup_info: bool
    author: str
    documentation_url: str

    @field_validator("documentation_url")
    @classmethod
    def validate_documentation_url(cls, value: str) -> str:
        """文档站地址为空时不显示，否则必须是无凭据的完整 HTTP(S) URL。"""
        if value != "" and not ValidationUtils.is_url(value):
            raise ValueError("文档站地址必须为空或有效的 HTTP(S) URL")
        return value
