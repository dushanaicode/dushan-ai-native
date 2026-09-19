from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from framework.common.enums.component_type_enum import ComponentTypeEnum
from framework.common.exception.constants.global_error_code_constants import (
    GlobalErrorCodeConstants,
)
from framework.common.exception.exceptions.configuration_exception import ConfigurationException
from framework.common.exception.registry.error_code_registry import ErrorCodeRegistry
from framework.common.page.core.data_paginator import DataPaginator
from framework.common.utils.cleanup_utils import CleanupUtils
from framework.starter_config.config.config_settings import ConfigSettings
from framework.starter_config.starter.config_starter import ConfigStarter
from framework.starter_database.pagination.sql_paginator import SqlPaginator
from framework.starter_di.starter.di_starter import DiStarter
from framework.starter_excel.config.excel_settings import ExcelSettings
from framework.starter_excel.starter.excel_starter import ExcelStarter
from framework.starter_i18n.core.i18n_locale_root import I18nLocaleRoot
from framework.starter_i18n.starter.i18n_starter import I18nStarter
from framework.starter_module.starter.module_starter import ModuleStarter
from framework.starter_scanner.starter.scanner_starter import ScannerStarter
from framework.starter_web.exception.validation_error_mapper import ValidationErrorMapper
from framework.starter_web.response.file_result import FileResult
from server.bootstrap.application_definitions import ApplicationDefinitions
from server.bootstrap.context import AppBootstrapContext


class DefinitionsStep:
    """按配置、定义和容器的真实依赖顺序装配，全部成功后发布应用快照。"""

    @staticmethod
    @asynccontextmanager
    async def run(ctx: AppBootstrapContext) -> AsyncIterator[None]:
        ctx.logger.info("【DefinitionsStep 】开始装配模块定义与国际化")
        modules, roots = ModuleStarter.initialize(ctx.module_settings)
        result = ScannerStarter.initialize(ctx.scanner_config, roots, modules)
        config_starter = ConfigStarter()
        configuration = config_starter.open(ctx.bootstrap_config, result)
        di_starter = DiStarter()
        application_context = None
        primary: BaseException | None = None
        published = False
        try:
            classes = tuple(
                dict.fromkeys(
                    (
                        GlobalErrorCodeConstants,
                        *result.get_components(component_type=ComponentTypeEnum.ERROR_CODE),
                    )
                )
            )
            registry = ErrorCodeRegistry(classes)
            message_keys = tuple(value.message_key for value in registry.get_all().values())
            message_keys += tuple(f"validation.{key}" for key in ValidationErrorMapper.messages)
            message_keys += tuple(
                key for module in modules for key in module.definition.required_message_keys
            )
            module_resources = []
            if ctx.i18n_options.enabled:
                for module in modules:
                    for resource in module.definition.resource_roots:
                        path = (module.root / resource.path).resolve()
                        if not path.is_relative_to(module.root):
                            raise ConfigurationException(
                                msg=f"模块语言资源越界: {module.definition.name} ({resource.path})"
                            )
                        module_resources.append(
                            I18nLocaleRoot(
                                path=path, scope=resource.scope, required=resource.required
                            )
                        )
            options = ctx.i18n_options.model_copy(
                update={"resource_roots": (*module_resources, *ctx.i18n_options.resource_roots)}
            )
            translator = I18nStarter.initialize(
                options, base_dir=ctx.base_dir, message_keys=message_keys
            )
            if ctx.di_settings.enabled:
                instances = {
                    ConfigSettings: ctx.bootstrap_config.get_config(
                        ConfigSettings, prefix="CONFIG_"
                    ),
                    type(ctx.settings): ctx.settings,
                    type(ctx.date_utils): ctx.date_utils,
                    type(ctx.expression_utils): ctx.expression_utils,
                    type(ctx.page_settings): ctx.page_settings,
                    type(ctx.response_settings): ctx.response_settings,
                    FileResult: FileResult(ctx.response_settings),
                    DataPaginator: DataPaginator(ctx.page_settings),
                    SqlPaginator: SqlPaginator(ctx.page_settings),
                    type(ctx.bootstrap_config): ctx.bootstrap_config,
                    ErrorCodeRegistry: registry,
                    type(translator): translator,
                }
                if ExcelSettings in configuration.model_classes:
                    instances.update(
                        ExcelStarter.initialize(configuration.get_config(ExcelSettings))
                    )
                application_context = await di_starter.open(
                    result.get_components(component_type=ComponentTypeEnum.COMPONENT),
                    configuration=configuration,
                    settings=ctx.di_settings,
                    enabled_modules=frozenset(module.definition.name for module in modules),
                    instances=instances,
                )
            else:
                ctx.logger.info("【DiStarter 】依赖注入未启用")
                ctx.logger.info("【ExcelStarter 】未启用 DI，导入导出组件未自动装配")
            snapshot = ApplicationDefinitions(
                modules, result, registry, translator, configuration, application_context
            )
            ctx.definitions = snapshot
            ctx.exception_handler.translator = translator
            ctx.middleware_result.translator = translator
            ctx.app.state.application_context = application_context
            published = True
            ctx.logger.info(
                "【DefinitionsStep 】定义装配完成：模块 {}，文件 {}，组件 {}，配置模型 {}，扫描 {:.1f}ms",
                len(modules),
                len(result.files),
                len(result.definitions),
                len(configuration.model_classes),
                result.duration_seconds * 1000,
            )
            yield
        except BaseException as error:
            primary = error
            raise
        finally:
            if published:
                ctx.exception_handler.translator = None
                ctx.middleware_result.translator = None
                ctx.definitions = None
                ctx.app.state.application_context = None
            cleanup_error, cancellation = (None, None)
            if di_starter.application is not None:
                cleanup_error, cancellation = await CleanupUtils.run_cancellation_safe_cleanup(
                    di_starter.close, "应用 DI 清理"
                )
            config_starter.close()
            errors = [] if cleanup_error is None else [cleanup_error]
            if cleanup_error is not None and primary is not None and primary.__cause__ is not None:
                errors.insert(0, primary.__cause__)
            CleanupUtils.raise_collected_cleanup_errors(
                "应用定义装配及清理失败",
                errors,
                caller_cancellation=cancellation,
                primary_error=primary,
            )
