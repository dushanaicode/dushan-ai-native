from time import perf_counter

from framework.common.importing.package_locator import PackageLocator
from framework.starter_module.resolved_module import ResolvedModule
from framework.starter_scanner.core.component_collector import ComponentCollector
from framework.starter_scanner.core.scan_result import ScanResult
from framework.starter_scanner.exception.scanner_error_codes import ScannerErrorCodes
from framework.starter_scanner.exception.scanner_exception import ScannerException


class DefinitionLoader:
    """加载已启用模块显式列出的原类，复用扫描定义校验，不遍历业务目录。"""

    @staticmethod
    def load(modules: tuple[ResolvedModule, ...]) -> ScanResult:
        started = perf_counter()
        requests = []
        for item in modules:
            for reference in item.definition.definitions:
                relative, name = reference.split(":")
                package = item.definition.package
                if relative != ".":
                    package += "." + relative
                source = PackageLocator.locate(package)
                if not source.is_relative_to(item.root):
                    raise ScannerException(
                        error_code=ScannerErrorCodes.SCANNER_SECURITY_ERROR,
                        msg=f"显式定义越出模块：{item.definition.name} ({reference})",
                    )
                requests.append((item.definition.name, package, name, source))
        definitions, loaded = [], {}
        for owner, package, name, source in requests:
            if package not in loaded:
                try:
                    loaded[package] = PackageLocator.import_source(package, source)
                except Exception as error:
                    raise ScannerException(
                        error_code=ScannerErrorCodes.SCANNER_MODULE_IMPORT_ERROR,
                        msg=f"显式定义导入失败：{package} ({source})；原因类型 {type(error).__name__}",
                        cause=error,
                    ) from error
            module = loaded[package]
            definitions.append(
                ComponentCollector.definition(vars(module).get(name), module, owner, source)
            )
        return ScanResult(
            tuple(definitions),
            tuple(sorted({row[3] for row in requests})),
            perf_counter() - started,
        )
