from dataclasses import dataclass

from framework.common.exception.registry.error_code_registry import ErrorCodeRegistry
from framework.common.i18n.core.translator import I18nTranslator
from framework.starter_config.provider.config_provider import ConfigProvider
from framework.starter_di.context.application_context import ApplicationContext
from framework.starter_module.core.resolved_module import ResolvedModule
from framework.starter_scanner.core.scan_result import ScanResult


@dataclass(frozen=True, slots=True)
class ApplicationDefinitions:
    """全部定义与语言校验成功后发布的应用快照，生命周期结束时释放引用。"""

    modules: tuple[ResolvedModule, ...]
    scan_result: ScanResult
    error_codes: ErrorCodeRegistry
    translator: I18nTranslator
    configuration: ConfigProvider
    application_context: ApplicationContext | None
