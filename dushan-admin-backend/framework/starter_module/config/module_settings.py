import json

from pydantic import BaseModel, ConfigDict, field_validator

from framework.common.importing.package_locator import PackageLocator


class ModuleSettings(BaseModel):
    """配置已安装的声明包和启用 ID；空 enabled 明确表示不启用模块。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    packages: tuple[str, ...]
    enabled: tuple[str, ...]

    @field_validator("packages", "enabled", mode="before")
    @classmethod
    def parse_array(cls, value: object) -> object:
        """环境覆盖使用 JSON 数组，值和结构随后统一校验。"""
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                raise ValueError("模块列表必须是 JSON 数组") from None
            if not isinstance(value, list):
                raise ValueError("模块列表必须是 JSON 数组")
        return value

    @field_validator("packages", "enabled")
    @classmethod
    def validate_names(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        """包名与 ID 明确且不重复，不把重复配置静默合并。"""
        if len(values) != len(set(values)):
            raise ValueError("不允许重复项")
        if any(not PackageLocator.is_valid_name(value) for value in values):
            raise ValueError("必须使用合法点分标识符")
        return values
