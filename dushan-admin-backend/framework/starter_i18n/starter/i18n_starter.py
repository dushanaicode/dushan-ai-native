from pathlib import Path

from loguru import logger

from framework.starter_i18n.core.i18n_locale_root import I18nLocaleRoot
from framework.starter_i18n.core.i18n_options import I18nOptions
from framework.starter_i18n.core.loader import I18nLoader
from framework.starter_i18n.core.parser import AcceptLanguageParser
from framework.starter_i18n.core.reloader import I18nReloader
from framework.starter_i18n.core.translator import I18nTranslator
from framework.starter_i18n.core.validator import I18nValidator


class I18nStarter:
    """按显式配置构建独立翻译器，不持有 Web 应用或全局注册状态。"""

    @staticmethod
    def _default_locales_root() -> Path:
        """定位随框架打包的内置语言资源。"""
        return Path(__file__).resolve().parent.parent / "locales"

    @staticmethod
    def initialize(
        options: I18nOptions,
        *,
        base_dir: Path,
        message_keys: tuple[str, ...] = (),
    ) -> I18nTranslator:
        """解析资源路径并完成首次加载，按配置选择是否启用热更新。"""
        logger.info("【I18nStarter 】开始装配国际化资源")
        message_keys = tuple(dict.fromkeys((*message_keys, *options.required_message_keys)))
        roots: list[I18nLocaleRoot] = []
        if options.include_builtin:
            roots.append(
                I18nLocaleRoot(
                    path=I18nStarter._default_locales_root(), scope="framework", required=True
                )
            )
        for root in options.resource_roots:
            roots.append(
                I18nLocaleRoot(
                    path=(base_dir / root.path).resolve(),
                    scope=root.scope,
                    required=root.required,
                )
            )
        loader = I18nLoader(options=options, locale_roots=tuple(roots))
        parser = AcceptLanguageParser(options)
        if options.enabled:
            logger.info("【I18nStarter 】资源范围已登记：{} 个，开始加载语言目录", len(roots))
        if options.enabled and options.hot_reload:
            reloader = I18nReloader(loader, message_keys=message_keys)
            logger.info("【I18nStarter 】初始化完成，资源热更新已启用")
            return I18nTranslator(reloader.catalog, parser, reloader=reloader)
        catalog = loader.load()
        if options.enabled:
            I18nValidator.validate(catalog, message_keys)
            logger.info("【I18nStarter 】初始化完成，资源热更新未启用")
        else:
            logger.info("【I18nStarter 】国际化未启用，使用原始消息键")
        return I18nTranslator(catalog, parser)
