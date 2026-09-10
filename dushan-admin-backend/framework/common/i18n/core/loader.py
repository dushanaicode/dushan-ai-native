import hashlib
import json
from collections.abc import Iterator
from pathlib import Path

from framework.common.exception.exceptions.configuration_exception import ConfigurationException
from framework.common.i18n.core.catalog import I18nBundles, I18nCatalog, I18nResource
from framework.common.i18n.core.i18n_locale_root import I18nLocaleRoot
from framework.common.i18n.core.i18n_options import I18nOptions


class I18nLoader:
    """按配置加载根目录中的 JSON，并用相同文件集合生成内容快照。

    使用 I18nLoader(options=options, locale_roots=roots) 显式提供资源根。
    每个根直接包含语言标签命名的 JSON；同一 scope 后面的根覆盖前面的同名 key。
    资源根的真实路径不能重复，避免同一份资源在一个版本中被重复读取。
    """

    def __init__(self, *, options: I18nOptions, locale_roots: tuple[I18nLocaleRoot, ...]) -> None:
        """保存配置及有序资源根，不自动添加内置目录或扫描旧布局。"""
        self.options = options
        self.locale_roots = tuple(locale_roots)
        resolved_roots: set[Path] = set()
        for root in self.locale_roots:
            try:
                resolved = root.path.resolve()
            except (OSError, RuntimeError) as exc:
                raise ConfigurationException(
                    msg=f"i18n 资源根目录路径解析失败: {root.path}"
                ) from exc
            if resolved in resolved_roots:
                raise ConfigurationException(msg=f"i18n 资源根目录的真实路径不能重复: {root.path}")
            resolved_roots.add(resolved)

    def load(self) -> I18nCatalog:
        """通过统一的版本加载入口返回 Catalog。"""
        return self.load_version()[0]

    def load_version(self) -> tuple[I18nCatalog, dict[str, str]]:
        """返回资源及实际加载字节的哈希；每个文件仅读取一次，后根覆盖前根。"""
        bundles: I18nBundles = {}
        snapshot: dict[str, str] = {}
        for scope, locale, path in self._iter_locale_files():
            try:
                raw = path.read_bytes()
                # 保留资源入口路径，两个文件链接不能合并成同一条快照记录。
                snapshot[str(path.absolute())] = hashlib.sha256(raw).hexdigest()
            except OSError as exc:
                raise ConfigurationException(msg=f"i18n 语言包读取失败: {path}") from exc
            resource = bundles.setdefault(locale, {}).setdefault(scope, {})
            resource.update(self._load_json(path, raw))
        return I18nCatalog(bundles=bundles, options=self.options), snapshot

    def snapshot(self) -> dict[str, str]:
        """为实际启用的文件生成 SHA256，包含新增、删除和等大小内容变化。"""
        snapshot: dict[str, str] = {}
        for _, _, path in self._iter_locale_files():
            try:
                snapshot[str(path.absolute())] = hashlib.sha256(path.read_bytes()).hexdigest()
            except OSError as exc:
                raise ConfigurationException(msg=f"i18n 语言包读取失败: {path}") from exc
        return snapshot

    def _iter_locale_files(self) -> Iterator[tuple[str, str, Path]]:
        """加载与快照共用筛选规则；禁用的语言、scope 和子目录均不读取。"""
        if not self.options.enabled:
            return
        for root in self.locale_roots:
            if not self._scope_enabled(root.scope):
                continue
            try:
                paths = sorted(root.path.iterdir())
            except FileNotFoundError as exc:
                if not root.required:
                    continue
                raise ConfigurationException(
                    msg=f"i18n 必需的资源根目录不存在: {root.path}"
                ) from exc
            except OSError as exc:
                raise ConfigurationException(msg=f"i18n 资源根目录读取失败: {root.path}") from exc
            for path in paths:
                if path.suffix != ".json" or path.stem not in self.options.supported_locales:
                    continue
                try:
                    if path.is_file():
                        yield root.scope, path.stem, path
                except OSError as exc:
                    raise ConfigurationException(msg=f"i18n 语言包读取失败: {path}") from exc

    def _scope_enabled(self, scope: str) -> bool:
        """None 表示全选，空元组表示全不选，父 scope 同时启用其子 scope。"""
        scopes = self.options.scopes
        return scopes is None or any(
            scope == selected or scope.startswith(selected + ".") for selected in scopes
        )

    @staticmethod
    def _load_json(path: Path, raw: bytes) -> I18nResource:
        """解析同一份已读取字节；错误保留路径及异常链，不附带资源值。"""
        try:
            data = json.loads(raw.decode("utf-8"), object_pairs_hook=I18nLoader._json_object)
            if not isinstance(data, dict):
                raise ConfigurationException(msg=f"i18n 语言包根节点必须是 JSON object: {path}")
            resource: I18nResource = {}
            I18nLoader._flatten_json(data, path, resource)
            return resource
        except UnicodeError as exc:
            raise ConfigurationException(msg=f"i18n 语言包读取失败: {path}") from exc
        except ValueError as exc:
            raise ConfigurationException(
                msg=f"i18n 语言包 JSON 格式错误或包含重复键: {path}"
            ) from exc
        except RecursionError as exc:
            raise ConfigurationException(msg=f"i18n 语言包 JSON 嵌套过深: {path}") from exc

    @staticmethod
    def _json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
        """在 JSON 解码时拒绝重复字段，避免后值静默覆盖前值。"""
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"i18n JSON 包含重复字段: {key}")
            result[key] = value
        return result

    @staticmethod
    def _flatten_json(
        data: dict[str, object], path: Path, resource: I18nResource, prefix: str = ""
    ) -> None:
        """将嵌套对象变为点分 key，并拒绝平铺字段与嵌套字段的同名碰撞。"""
        for key, value in data.items():
            if any(not part or part != part.strip() for part in key.split(".")):
                raise ConfigurationException(
                    msg=f"i18n 字段名不能包含空段或首尾空白: {path}, key={key}"
                )
            message_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                I18nLoader._flatten_json(value, path, resource, message_key)
            elif not isinstance(value, str) or not value:
                raise ConfigurationException(
                    msg=f"i18n 翻译必须是非空字符串或嵌套对象: {path}, key={message_key}"
                )
            elif message_key in resource:
                raise ConfigurationException(
                    msg=f"i18n 点分 key 与嵌套字段碰撞: {path}, key={message_key}"
                )
            else:
                resource[message_key] = value
