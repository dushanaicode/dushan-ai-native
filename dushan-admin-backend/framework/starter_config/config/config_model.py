from pydantic import BaseModel, ConfigDict


class ConfigModel(BaseModel):
    """模块配置模型基类；字段只声明类型/约束，部署默认值放公共 YAML。"""

    model_config = ConfigDict(extra="forbid", frozen=True)
