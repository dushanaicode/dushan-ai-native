from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class I18nLocaleRoot(BaseModel):
    """声明一个资源目录及其 scope，目录中直接放置语言标签命名的 JSON。

    例如 path="modules/account/i18n"、scope="account"，目录包含 zh-CN.json。
    相对路径由应用按配置根目录解析；required=False 允许可选模块尚未提供资源。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    path: Path
    scope: str = Field(pattern="^[A-Za-z_][A-Za-z0-9_]*(?:\\.[A-Za-z_][A-Za-z0-9_]*)*$")
    required: bool
