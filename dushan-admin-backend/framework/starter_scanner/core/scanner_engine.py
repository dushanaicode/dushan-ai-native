from pathlib import Path
from time import perf_counter

from loguru import logger

from framework.common.importing.package_locator import PackageLocator
from framework.starter_scanner.config.scanner_config import ScannerConfig
from framework.starter_scanner.core.component_collector import ComponentCollector
from framework.starter_scanner.core.component_definition import ComponentDefinition
from framework.starter_scanner.core.scan_recorder import ScanRecorder
from framework.starter_scanner.core.scan_result import ScanResult
from framework.starter_scanner.core.scan_root import ScanRoot
from framework.starter_scanner.definitions.constants.scanner_error_codes import ScannerErrorCodes
from framework.starter_scanner.exception.scanner_exception import ScannerException
from framework.starter_scanner.filter.path_filter import PathFilter


class ScannerEngine:
    """同步发现可信源码中的静态定义，每次调用独立构建并一次返回。

    不创建线程、不承诺 import 硬超时或撤销副作用。先完成整份文件来源预检，
    再使用正常 import 身份；Python 缓存可共享，应用结果始终独立。
    """

    def __init__(self, config: ScannerConfig) -> None:
        self.config = config
        self._filter = PathFilter(config)
        self._collector = ComponentCollector(config)
        self._ignored = frozenset(name.casefold() for name in config.ignored_directories)

    def scan(self, roots: tuple[ScanRoot, ...]) -> ScanResult:
        """禁用或明确全不选时不定位扫描根；合法空结果正常返回。

        忽略目录规则只作用于扫描根内部的子目录，显式声明的扫描根本身不受影响。
        """
        started = perf_counter()
        recorder = (
            ScanRecorder(self.config.diagnostic_limit) if self.config.diagnostics_enabled else None
        )
        if not self.config.enabled or self.config.component_types == ():
            logger.info("【ScannerStarter 】自动扫描未启用或未选择组件类型，跳过源码扫描")
            if recorder is not None:
                recorder.skip(
                    "automatic_disabled" if not self.config.enabled else "empty_type_filter", ""
                )
            return ScanResult(
                (), (), perf_counter() - started, None if recorder is None else recorder.snapshot()
            )
        logger.info("【ScannerStarter 】开始扫描：{} 个扫描根", len(roots))
        files: dict[str, tuple[str, Path]] = {}
        for root in roots:
            reason = self._filter.reason(root.package, traverse=True)
            if reason is not None:
                if recorder is not None:
                    recorder.skip(reason, root.package)
                continue
            path = self._resolve_root(root)
            if PackageLocator.locate(root.package, package=True) != path / "__init__.py":
                raise ScannerException(
                    error_code=ScannerErrorCodes.SCANNER_SECURITY_ERROR,
                    msg=f"扫描根与包来源不匹配: {root.package} ({path})",
                )
            self._collect_files(root.module, root.package, path, path, files, recorder)
        if recorder is not None:
            recorder.phases["enumeration"] = perf_counter() - started
        logger.info("【ScannerStarter 】文件枚举完成：{} 个，开始校验导入来源", len(files))
        validation_started = perf_counter()
        physical: dict[Path, str] = {}
        for name, (_, path) in sorted(files.items()):
            if path in physical and physical[path] != name:
                raise ScannerException(
                    error_code=ScannerErrorCodes.SCANNER_SECURITY_ERROR,
                    msg=f"同一源码有多个导入名: {physical[path]} / {name} ({path})",
                )
            physical[path] = name
            if PackageLocator.locate(name) != path:
                raise ScannerException(
                    error_code=ScannerErrorCodes.SCANNER_SECURITY_ERROR,
                    msg=f"扫描文件与导入来源不匹配: {name} ({path})",
                )
        if recorder is not None:
            recorder.phases["validation"] = perf_counter() - validation_started
        logger.info("【ScannerStarter 】来源校验通过，开始导入源码并收集组件定义")
        definitions: list[ComponentDefinition] = []
        for name, (owner, path) in sorted(files.items()):
            import_started = perf_counter() if recorder is not None else 0.0
            try:
                module = PackageLocator.import_source(name, path)
            except Exception as error:
                raise ScannerException(
                    error_code=ScannerErrorCodes.SCANNER_MODULE_IMPORT_ERROR,
                    msg=f"模块导入失败: {name} ({path})；原因类型 {type(error).__name__}",
                    cause=error,
                ) from error
            if recorder is not None:
                recorder.imported(name, perf_counter() - import_started)
            collection_started = perf_counter() if recorder is not None else 0.0
            found = self._collector.collect(module, owner, path)
            # logger.debug("【ScannerStarter 】已扫描 {}，发现 {} 个定义", name, len(found))
            definitions.extend(found)
            if recorder is not None:
                recorder.phases["collection"] += perf_counter() - collection_started
                if not found:
                    recorder.skip("no_matching_definitions", name)
        logger.info(
            "【ScannerStarter 】扫描完成：文件 {} 个，定义 {} 个，耗时 {:.1f}ms",
            len(files),
            len(definitions),
            (perf_counter() - started) * 1000,
        )
        return ScanResult(
            tuple(definitions),
            tuple(path for _, path in (files[name] for name in sorted(files))),
            perf_counter() - started,
            None if recorder is None else recorder.snapshot(),
        )

    @staticmethod
    def _resolve_root(root: ScanRoot) -> Path:
        """扫描根不存在、不可访问或不是目录时，报告模块、包、路径与原始原因。"""
        try:
            path = root.path.resolve(strict=True)
            directory = path.is_dir()
        except (OSError, RuntimeError) as error:
            raise ScannerException(
                error_code=ScannerErrorCodes.SCANNER_CONFIG_ERROR,
                msg=(
                    f"扫描根目录不存在或无法访问: {root.package} ({root.path})；"
                    f"模块 {root.module}；原因类型 {type(error).__name__}"
                ),
                cause=error,
            ) from error
        if not directory:
            raise ScannerException(
                error_code=ScannerErrorCodes.SCANNER_CONFIG_ERROR,
                msg=f"扫描根不是目录: {root.package} ({path})；模块 {root.module}",
            )
        return path

    def _collect_files(
        self,
        owner: str,
        package: str,
        directory: Path,
        allowed: Path,
        files: dict[str, tuple[str, Path]],
        recorder: ScanRecorder | None,
    ) -> None:
        """只遍历普通包，拒绝包内链接/联接，过滤先于子包枚举与导入。

        以点开头的条目不是合法 Python 名称，始终跳过；配置的忽略目录按目录名
        不区分大小写匹配，在任何来源校验和导入之前剪枝，不影响 .py 文件。
        """
        if self._filter.accepts(package):
            self._add_file(files, package, owner, directory / "__init__.py")
        for path in self._entries(package, directory):
            if path.name == "__init__.py":
                continue
            name = f"{package}.{path.stem if path.suffix == '.py' else path.name}"
            if path.name.startswith("."):
                if recorder is not None:
                    recorder.skip("hidden_path", str(path))
                continue
            if path.name.casefold() in self._ignored and path.is_dir():
                if recorder is not None:
                    recorder.skip("ignored_directory", name)
                continue
            reason = self._filter.reason(name, traverse=True)
            if reason is not None:
                if recorder is not None:
                    recorder.skip(reason, name)
                continue
            if path.is_symlink() or path.is_junction():
                raise ScannerException(
                    error_code=ScannerErrorCodes.SCANNER_SECURITY_ERROR,
                    msg=f"扫描范围不允许符号链接或目录联接: {path}",
                )
            if not path.resolve().is_relative_to(allowed):
                raise ScannerException(
                    error_code=ScannerErrorCodes.SCANNER_SECURITY_ERROR,
                    msg=f"扫描文件越出允许目录: {path}",
                )
            if path.is_dir():
                if (path / "__init__.py").is_file() and PackageLocator.is_valid_name(name):
                    self._collect_files(owner, name, path, allowed, files, recorder)
                elif recorder is not None:
                    recorder.skip("not_python_package", name)
            elif path.suffix == ".py" and self._filter.accepts(name):
                self._add_file(files, name, owner, path)
            elif recorder is not None:
                recorder.skip("not_selected_python_file", name)

    @staticmethod
    def _entries(package: str, directory: Path) -> list[Path]:
        """目录无法读取时给出包名、路径与原始原因，而不是泄漏底层 OSError。"""
        try:
            return sorted(directory.iterdir())
        except OSError as error:
            raise ScannerException(
                error_code=ScannerErrorCodes.SCANNER_CONFIG_ERROR,
                msg=f"扫描目录无法读取: {package} ({directory})；原因类型 {type(error).__name__}",
                cause=error,
            ) from error

    @staticmethod
    def _add_file(files: dict[str, tuple[str, Path]], name: str, owner: str, path: Path) -> None:
        """重叠扫描根可去重，跨模块归属冲突不能静默覆盖。"""
        if path.is_symlink() or not path.resolve().is_relative_to(path.parent):
            raise ScannerException(
                error_code=ScannerErrorCodes.SCANNER_SECURITY_ERROR,
                msg=f"扫描文件存在链接或越界: {path}",
            )
        try:
            entry = (owner, path.resolve(strict=True))
        except OSError as error:
            raise ScannerException(
                error_code=ScannerErrorCodes.SCANNER_CONFIG_ERROR,
                msg=f"扫描文件不存在或无法访问: {name} ({path})；原因类型 {type(error).__name__}",
                cause=error,
            ) from error
        if name in files and files[name] != entry:
            raise ScannerException(
                error_code=ScannerErrorCodes.SCANNER_CONFIG_ERROR,
                msg=f"扫描文件归属冲突: {name} ({path})",
            )
        files[name] = entry
