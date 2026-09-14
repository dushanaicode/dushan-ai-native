from collections.abc import Sequence

from loguru import logger

from framework.common.exception.exceptions.configuration_exception import ConfigurationException
from framework.starter_i18n.core.catalog import I18nCatalog
from framework.starter_i18n.core.parser import AcceptLanguageParser
from framework.starter_i18n.core.reloader import I18nReloader


class I18nTranslator:
    """组合语言选择、资源查询和模板格式化，可直接注入异常处理器。

    translate 指定 scope，translate_any_scope 使用全局唯一的 message_key。
    args 只作用于命中的翻译模板；default 是已完成且可公开的文本。
    一次调用持有同一个不可变 Catalog，热更新不会把两版资源混入同一次查询。
    """

    def __init__(
        self,
        catalog: I18nCatalog,
        parser: AcceptLanguageParser,
        *,
        reloader: I18nReloader | None = None,
    ) -> None:
        """保存实例依赖，不读取应用状态或全局注册表。"""
        self._catalog = catalog
        self._parser = parser
        self._reloader = reloader

    def translate(
        self,
        message_key: str | None,
        accept_language: str | None,
        *,
        scope: str,
        default: str | None = None,
        args: Sequence[object] | None = None,
    ) -> str:
        """在指定 scope 内选择语言并格式化命中的翻译模板。"""
        return self._translate(
            message_key, accept_language, scope=scope, default=default, args=args
        )

    def translate_any_scope(
        self,
        message_key: str | None,
        accept_language: str | None,
        *,
        default: str | None = None,
        args: Sequence[object] | None = None,
    ) -> str:
        """按全局唯一的消息键翻译，参数名与异常翻译协议一致。"""
        return self._translate(message_key, accept_language, scope=None, default=default, args=args)

    @property
    def catalog(self) -> I18nCatalog:
        """返回当前已发布的资源版本，不触发文件扫描。"""
        return self._reloader.catalog if self._reloader is not None else self._catalog

    def _translate(
        self,
        message_key: str | None,
        accept_language: str | None,
        *,
        scope: str | None,
        default: str | None,
        args: Sequence[object] | None,
    ) -> str:
        """一次解析语言和查询资源，格式失败只在模板边界处理。"""
        catalog = self._reloader.get_catalog() if self._reloader is not None else self._catalog
        if not catalog.options.enabled or not message_key:
            return default if default is not None else message_key or ""
        locale = self._parser.detect_lang(accept_language)
        raw = catalog.resolve(message_key, locale, scope=scope)
        if raw is None:
            return catalog.missing_text(message_key, locale, default=default, scope=scope)
        try:
            return raw.format(*(args if args is not None else ()))
        except Exception as error:
            if catalog.options.format_error_policy == "error":
                raise ConfigurationException(
                    msg=f"i18n 翻译模板格式化失败: {message_key}"
                ) from error
            logger.warning(
                "i18n 翻译模板格式化失败：key={}，异常类型={}", message_key, type(error).__name__
            )
            return default if default is not None else message_key
