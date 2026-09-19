from dataclasses import dataclass
from pathlib import Path

from framework.common.enums.component_type_enum import ComponentTypeEnum
from framework.starter_scanner.core.component_definition import ComponentDefinition
from framework.starter_scanner.core.scan_diagnostics import ScanDiagnostics
from framework.starter_scanner.definitions.constants.scanner_error_codes import ScannerErrorCodes
from framework.starter_scanner.exception.scanner_exception import ScannerException


@dataclass(frozen=True, slots=True)
class ScanResult:
    """一次完整扫描的不可变结果；失败没有返回值，不修改已成功的结果。"""

    definitions: tuple[ComponentDefinition, ...]
    files: tuple[Path, ...]
    duration_seconds: float
    diagnostics: ScanDiagnostics | None = None

    def merge_explicit(self, explicit: "ScanResult") -> "ScanResult":
        """显式定义与自动发现合成一个目录；同类同归属去重，冲突明确失败。"""
        definitions = {}
        for definition in (*self.definitions, *explicit.definitions):
            previous = definitions.get(definition.component)
            if previous is not None and previous != definition:
                raise ScannerException(
                    error_code=ScannerErrorCodes.SCANNER_CONFIG_ERROR,
                    msg=f"定义来源或归属冲突：{definition.component.__module__}.{definition.component.__qualname__}",
                )
            definitions[definition.component] = definition
        return ScanResult(
            tuple(
                sorted(
                    definitions.values(),
                    key=lambda item: (
                        item.module,
                        item.component.__module__,
                        item.component.__qualname__,
                    ),
                )
            ),
            tuple(sorted(set(self.files) | set(explicit.files))),
            self.duration_seconds + explicit.duration_seconds,
            self.diagnostics,
        )

    def get_components(
        self, *, module: str | None = None, component_type: ComponentTypeEnum | None = None
    ) -> tuple[type, ...]:
        """按声明模块和类别查询，结果仍是类定义，不触发额外导入。"""
        return tuple(
            item.component
            for item in self.definitions
            if (module is None or item.module == module)
            and (component_type is None or item.metadata.component_type == component_type)
        )
