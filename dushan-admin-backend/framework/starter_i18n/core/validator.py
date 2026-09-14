from collections.abc import Iterable

from loguru import logger

from framework.common.exception.exceptions.configuration_exception import ConfigurationException
from framework.starter_i18n.core.catalog import I18nCatalog


class I18nValidator:
    """校验调用方声明的消息集合是否覆盖全部配置语言。"""

    @staticmethod
    def validate(catalog: I18nCatalog, message_keys: Iterable[str]) -> list[tuple[str, str]]:
        """仅检查精确语言；错误策略阻止启用，警告策略返回缺失清单。"""
        options = catalog.options
        if not options.enabled or not options.validate_translations:
            return []
        keys = tuple(dict.fromkeys(key for key in message_keys if key))
        if not keys:
            logger.info("【I18n】未提供 message_key，跳过翻译完整性校验")
            return []
        missing = [
            (message_key, locale)
            for message_key in keys
            for locale in options.supported_locales
            if not catalog.has_translation(message_key, locale)
        ]
        if not missing:
            logger.info(
                "【I18n】翻译完整性校验通过: {} 个 key，{} 种语言",
                len(keys),
                len(options.supported_locales),
            )
            return []
        details = "\n".join(f"  - key={key}, locale={locale}" for key, locale in missing[:20])
        if len(missing) > 20:
            details += f"\n  ... 及 {len(missing) - 20} 条更多"
        message = f"i18n 完整性校验发现 {len(missing)} 项缺失翻译:\n{details}"
        if options.validation_policy == "error":
            logger.error("【I18n】{}", message)
            raise ConfigurationException(msg=message)
        logger.warning("【I18n】{}", message)
        return missing
