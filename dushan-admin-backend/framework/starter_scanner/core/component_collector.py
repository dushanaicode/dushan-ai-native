from pathlib import Path
from types import ModuleType

from framework.common.component.component_metadata import ComponentMetadata
from framework.starter_scanner.config.scanner_config import ScannerConfig
from framework.starter_scanner.core.component_definition import ComponentDefinition
from framework.starter_scanner.exception.scanner_error_codes import ScannerErrorCodes
from framework.starter_scanner.exception.scanner_exception import ScannerException


class ComponentCollector:
    """只读取当前模块直接声明的类和自身标记，避免重导出、继承和动态属性干扰。"""

    def __init__(self, config: ScannerConfig) -> None:
        self.config = config

    def collect(
        self, module: ModuleType, owner: str, source: Path
    ) -> tuple[ComponentDefinition, ...]:
        """验证标记后按类别筛选，同一类的多个模块内别名只收一次。"""
        result = []
        seen: set[type] = set()
        for value in vars(module).values():
            if not isinstance(value, type) or value.__module__ != module.__name__ or value in seen:
                continue
            seen.add(value)
            namespace = vars(value)
            if ComponentMetadata.ATTRIBUTE not in namespace:
                continue
            definition = self.definition(value, module, owner, source)
            metadata = definition.metadata
            if (
                self.config.component_types is None
                or metadata.component_type in self.config.component_types
            ):
                result.append(definition)
        return tuple(sorted(result, key=lambda item: item.component.__qualname__))

    @staticmethod
    def definition(
        value: object, module: ModuleType, owner: str, source: Path
    ) -> ComponentDefinition:
        """显式与自动来源共用原类、直接声明和元数据校验。"""
        if not isinstance(value, type) or value.__module__ != module.__name__:
            raise ScannerException(
                error_code=ScannerErrorCodes.SCANNER_MISSING_METADATA,
                msg=f"定义必须是模块直接声明的类：{module.__name__} ({source})",
            )
        metadata = vars(value).get(ComponentMetadata.ATTRIBUTE)
        if not isinstance(metadata, ComponentMetadata):
            raise ScannerException(
                error_code=ScannerErrorCodes.SCANNER_MISSING_METADATA,
                msg=f"组件元数据非法: {module.__name__}.{value.__qualname__} ({source})",
            )
        return ComponentDefinition(value, owner, source, metadata)
