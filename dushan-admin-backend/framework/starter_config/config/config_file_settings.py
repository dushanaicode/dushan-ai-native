from pathlib import Path

from pydantic import BaseModel, ConfigDict


class ConfigFileSettings(BaseModel):
    """附加配置文件声明；相对路径以应用配置目录为基准。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    path: Path
    required: bool
