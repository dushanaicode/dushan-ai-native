from loguru import logger

from framework.starter_module.core.definition_loader import DefinitionLoader
from framework.starter_scanner.core.scanner_engine import ScannerEngine


class ScannerStarter:
    """按模块范围扫描源码，再合并显式声明，提供唯一的组件定义快照。"""

    @staticmethod
    def initialize(settings, roots, modules):
        result = ScannerEngine(settings).scan(roots)
        logger.info("【ScannerStarter 】开始加载模块显式组件声明")
        result = result.merge_explicit(DefinitionLoader.load(modules))
        logger.info(
            "【ScannerStarter 】定义发现完成：文件 {} 个，定义 {} 个",
            len(result.files),
            len(result.definitions),
        )
        return result
