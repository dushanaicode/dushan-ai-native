import json

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from framework.common.enums.component_type_enum import ComponentTypeEnum
from framework.common.importing.package_locator import PackageLocator


class ScannerConfig(BaseModel):
    """启动扫描策略；默认值只在 application.yaml，None 全选、空元组全不选。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    enabled: bool
    component_types: tuple[ComponentTypeEnum, ...] | None
    include_packages: tuple[str, ...] | None
    exclude_packages: tuple[str, ...]
    diagnostics_enabled: bool
    diagnostic_limit: int = Field(gt=0, le=100)

    @field_validator("diagnostic_limit", mode="before")
    @classmethod
    def reject_boolean_limit(cls, value: object) -> object:
        if isinstance(value, bool):
            raise ValueError("诊断条数不能是布尔值")
        return value

    @field_validator("component_types", "include_packages", "exclude_packages", mode="before")
    @classmethod
    def parse_array(cls, value: object) -> object:
        """环境变量接受 JSON 数组或 null，字段模型决定是否允许 null。"""
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                raise ValueError("扫描列表必须是 JSON 数组或 null") from None
            if value is not None and not isinstance(value, list):
                raise ValueError("扫描列表必须是 JSON 数组或 null")
        return value

    @field_validator("include_packages", "exclude_packages", "component_types")
    @classmethod
    def validate_list(cls, values: tuple | None, info: ValidationInfo) -> tuple | None:
        """包前缀按完整 Python 名称匹配，配置重复项明确拒绝。"""
        if values is not None:
            if len(values) != len(set(values)):
                raise ValueError("不允许重复项")
            if info.field_name != "component_types" and any(
                not PackageLocator.is_valid_name(value) for value in values
            ):
                raise ValueError("扫描包前缀必须使用合法点分标识符")
        return values
