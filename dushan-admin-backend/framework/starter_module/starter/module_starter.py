from loguru import logger

from framework.starter_module.core.module_loader import ModuleLoader
from framework.starter_scanner.core.scan_root import ScanRoot


class ModuleStarter:
    """读取模块声明并构建本应用的扫描范围，不执行模块生命周期。"""

    @staticmethod
    def initialize(settings):
        modules = ModuleLoader.load(settings)
        roots = tuple(
            ScanRoot(
                module.definition.name,
                module.definition.package
                if relative == "."
                else f"{module.definition.package}.{relative}",
                module.root if relative == "." else module.root.joinpath(*relative.split(".")),
            )
            for module in modules
            for relative in module.definition.scan_roots
        )
        logger.info("【ModuleStarter 】模块扫描范围装配完成：{} 个扫描根", len(roots))
        return modules, roots
