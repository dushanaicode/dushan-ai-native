from collections import OrderedDict
from collections.abc import Mapping
from threading import RLock
from types import MappingProxyType

from loguru import logger

from framework.common.exception.exceptions.configuration_exception import ConfigurationException
from framework.starter_i18n.core.i18n_options import I18nOptions

type I18nResource = dict[str, str]
type I18nLanguageBundle = dict[str, I18nResource]
type I18nBundles = dict[str, I18nLanguageBundle]


class I18nCatalog:
    """保存不可变的扁平语言资源，并管理有界缓存和缺失记录。

    例如 I18nCatalog({"en-US": {"account": {"user.created": "User created"}}}, options)。
    每层资源都会复制并设为只读；同一 key 在全部语言中只能属于一个 scope。
    """

    def __init__(
        self,
        bundles: Mapping[str, Mapping[str, Mapping[str, str]]],
        options: I18nOptions,
    ) -> None:
        """复制语言资源、检查 scope 唯一性，并创建当前版本的空缓存。"""
        self._options = options
        self._key_scopes: dict[str, str] = {}
        frozen_bundles: dict[str, Mapping[str, Mapping[str, str]]] = {}
        for locale, language_bundle in bundles.items():
            frozen_scopes: dict[str, Mapping[str, str]] = {}
            for scope, resource in language_bundle.items():
                copied_resource = dict(resource)
                for message_key, value in copied_resource.items():
                    if not isinstance(value, str) or not value:
                        raise ConfigurationException(
                            msg=f"i18n 翻译必须是非空字符串: scope={scope}, locale={locale}, key={message_key}"
                        )
                    previous_scope = self._key_scopes.setdefault(message_key, scope)
                    if previous_scope != scope:
                        raise ConfigurationException(
                            msg=f"i18n 翻译 key 不能跨 scope 重复: key={message_key}, scopes={previous_scope}, {scope}"
                        )
                frozen_scopes[scope] = MappingProxyType(copied_resource)
            frozen_bundles[locale] = MappingProxyType(frozen_scopes)
        self._bundles = MappingProxyType(frozen_bundles)
        self._resolve_cache: OrderedDict[tuple[str, str, str], str] = OrderedDict()
        self._missing_keys: OrderedDict[tuple[str | None, str, str], None] = OrderedDict()
        self._lock = RLock()

    @property
    def bundles(self) -> Mapping[str, Mapping[str, Mapping[str, str]]]:
        """返回只读资源视图，调用方不能改写已缓存的文案。"""
        return self._bundles

    @property
    def options(self) -> I18nOptions:
        """返回构建当前资源版本时使用的配置。"""
        return self._options

    def resolve(self, message_key: str, locale: str, *, scope: str | None = None) -> str | None:
        """静默查询翻译，按配置决定是否回退到默认语言。"""
        if not self.options.enabled or not message_key:
            return None
        selected_scope = scope if scope is not None else self._key_scopes.get(message_key)
        if selected_scope is None:
            return None
        cache_key = (selected_scope, locale, message_key)
        with self._lock:
            cached = self._resolve_cache.get(cache_key)
            if cached is not None:
                self._resolve_cache.move_to_end(cache_key)
                return cached
            locales = (locale,)
            if self.options.fallback_to_default and locale != self.options.default_locale:
                locales += (self.options.default_locale,)
            for candidate in locales:
                value = self.bundles.get(candidate, {}).get(selected_scope, {}).get(message_key)
                if value is not None:
                    if self.options.cache_size:
                        self._resolve_cache[cache_key] = value
                        if len(self._resolve_cache) > self.options.cache_size:
                            self._resolve_cache.popitem(last=False)
                    return value
        return None

    def has_translation(self, message_key: str, locale: str) -> bool:
        """精确检查指定语言，不借用默认语言或产生缺失记录。"""
        scope = self._key_scopes.get(message_key)
        return scope is not None and message_key in self.bundles.get(locale, {}).get(scope, {})

    def missing_text(
        self,
        message_key: str | None,
        locale: str,
        *,
        default: str | None = None,
        scope: str | None = None,
    ) -> str:
        """记录实际缺失，并按策略返回公开提示、key 或抛出配置异常。"""
        if not self.options.enabled or not message_key:
            return self._fallback_text(default, message_key)
        selected_scope = scope if scope is not None else self._key_scopes.get(message_key)
        self._record_missing(selected_scope, locale, message_key)
        if self.options.missing_policy == "error":
            raise ConfigurationException(
                msg=f"i18n 缺失翻译: scope={selected_scope}, locale={locale}, key={message_key}"
            )
        if self.options.missing_policy == "key":
            return message_key
        return self._fallback_text(default, message_key)

    def translate(
        self,
        message_key: str | None,
        locale: str,
        *,
        default: str | None = None,
        scope: str | None = None,
    ) -> str:
        """查询文案；未启用或空 key 直接返回调用方提示，不记录缺失。"""
        if not self.options.enabled or not message_key:
            return self._fallback_text(default, message_key)
        value = self.resolve(message_key, locale, scope=scope)
        if value is not None:
            return value
        return self.missing_text(message_key, locale, default=default, scope=scope)

    def _record_missing(self, scope: str | None, locale: str, message_key: str) -> None:
        """按首次出现顺序保留有界缺失记录，容量为零时不保存去重状态。"""
        entry = (scope, locale, message_key)
        with self._lock:
            if entry in self._missing_keys:
                return
            if self.options.missing_cache_size:
                self._missing_keys[entry] = None
                if len(self._missing_keys) > self.options.missing_cache_size:
                    self._missing_keys.popitem(last=False)
            if self.options.log_missing:
                logger.warning(
                    "【I18n 】缺失翻译: scope={}, locale={}, key={}", scope, locale, message_key
                )

    def get_missing_keys(self) -> set[tuple[str | None, str, str]]:
        """返回当前保留的缺失记录副本。"""
        with self._lock:
            return set(self._missing_keys)

    def clear_cache(self) -> None:
        """清空查询缓存，保留缺失记录。"""
        with self._lock:
            self._resolve_cache.clear()

    @staticmethod
    def _fallback_text(default: str | None, message_key: str | None) -> str:
        """调用方提供 default 时原样返回，否则返回 key。"""
        return default if default is not None else message_key or ""
