import inspect
import json
from collections.abc import Awaitable, Callable, Iterable, Mapping
from contextvars import ContextVar
from copy import deepcopy
from threading import RLock
from types import UnionType
from typing import TypeVar, Union, get_args, get_origin

from pydantic import BaseModel, ValidationError

from framework.common.security.sanitizer import Sanitizer
from framework.starter_config.config.config_settings import ConfigSettings
from framework.starter_config.decorator.config_model_metadata import ConfigModelMetadata
from framework.starter_config.enums.config_source_enum import ConfigSourceEnum
from framework.starter_config.provider.bootstrap_config_error import BootstrapConfigError
from framework.starter_config.provider.bootstrap_config_provider import BootstrapConfigProvider
from framework.starter_config.provider.config_change import ConfigChange
from framework.starter_config.provider.config_notification import ConfigNotification
from framework.starter_config.provider.config_snapshot import ConfigSnapshot
from framework.starter_config.provider.config_update_result import ConfigUpdateResult
from framework.starter_config.source.config_file_reader import ConfigFileReader
from framework.starter_config.source.config_values import ConfigValues

T = TypeVar("T", bound=BaseModel)
ConfigListener = Callable[[ConfigChange], None]
ConfigLoader = Callable[[], Awaitable[Mapping[str, object]]]


class ConfigProvider:
    """按模型声明构建应用独立配置，全部校验后才发布新版本。

    模型默认值位于 config.models.<name>；环境变量按明确前缀读取。
    get_config 返回独立模型副本；read 同时返回该版本的值、字段来源和版本号。
    内存/文件/外部快照刷新是显式操作，不启动监听线程，不隐式访问数据库。
    """

    def __init__(
        self,
        bootstrap: BootstrapConfigProvider,
        source_classes: Iterable[type[BaseModel]],
        *,
        external_values: Mapping[str, object] | None = None,
    ) -> None:
        self._bootstrap = bootstrap
        self._options = bootstrap.get_config(ConfigSettings, prefix="CONFIG_")
        self._lock = RLock()
        self._updates_lock = RLock()
        self._closed = False
        self._revision = 1
        self._listeners: list[ConfigListener] = []
        self._notifying = ContextVar(f"config_notify_{id(self)}", default=None)
        self._metadata: dict[type[BaseModel], ConfigModelMetadata] = {}
        names: set[str] = set()
        prefixes: set[str] = set()
        for model in dict.fromkeys(source_classes):
            metadata = vars(model).get(ConfigModelMetadata.ATTRIBUTE)
            if not isinstance(metadata, ConfigModelMetadata):
                raise BootstrapConfigError(
                    f"配置模型缺少自身声明：{model.__module__}.{model.__qualname__}"
                )
            self._validate_model(model, set())
            if metadata.name in names or metadata.env_prefix in prefixes:
                raise BootstrapConfigError(f"配置模型名称或环境前缀冲突：{metadata.name}")
            unknown = (
                metadata.field_keys.keys() | metadata.field_sources.keys()
            ) - model.model_fields.keys()
            if unknown:
                raise BootstrapConfigError(
                    f"配置模型声明了不存在的字段：{metadata.name} ({', '.join(sorted(unknown))})"
                )
            for order in (metadata.sources, *metadata.field_sources.values()):
                if order is not None and set(order) - set(self._options.source_order):
                    raise BootstrapConfigError(f"配置模型引用了未启用的配置源：{metadata.name}")
            names.add(metadata.name)
            prefixes.add(metadata.env_prefix)
            self._metadata[model] = metadata
        yaml_values, yaml_sources = bootstrap.get_yaml_snapshot()
        self._layers = {source: ({}, {}) for source in ConfigSourceEnum}
        self._layers[ConfigSourceEnum.YAML] = (self._flatten(yaml_values), yaml_sources)
        self._layers[ConfigSourceEnum.FILE] = self._read_files()
        if external_values is not None:
            flat = self._flatten(external_values)
            self._layers[ConfigSourceEnum.EXTERNAL] = (flat, dict.fromkeys(flat, "外部配置快照"))
        self._environment_layers = {
            model: self._model_environment(model, metadata)
            for model, metadata in self._metadata.items()
        }
        self._environment_trees = {
            model: ConfigValues.tree(layer[0]) for model, layer in self._environment_layers.items()
        }
        self._configs, self._origins = self._build(self._layers)

    @property
    def model_classes(self) -> tuple[type[BaseModel], ...]:
        return tuple(self._metadata)

    @property
    def revision(self) -> int:
        with self._lock:
            self._require_open()
            return self._revision

    def get_config(self, model: type[T]) -> T:
        """读取最新有效模型副本，不让调用方修改内部配置缓存。"""
        return self.read(model)[0]

    def snapshot(self) -> ConfigSnapshot:
        """一次锁内取得全部模型的同版本只读视图，供条件装配或业务一致读取。"""
        with self._lock:
            self._require_open()
            return ConfigSnapshot(self._configs, self._origins, self._revision)

    def get_sources(self, model: type[BaseModel]) -> dict[str, str]:
        """只返回字段来源名称，不暴露原始值。"""
        return self.read(model)[1]

    def read(self, model: type[T]) -> tuple[T, dict[str, str], int]:
        """一次锁内取得同一版本的模型、来源及版本号。"""
        with self._lock:
            self._require_open()
            if model not in self._configs:
                raise BootstrapConfigError(
                    f"配置模型未注册：{model.__module__}.{model.__qualname__}"
                )
            return (
                self._configs[model].model_copy(deep=True),
                dict(self._origins[model]),
                self._revision,
            )

    def export_values(self) -> dict[str, object]:
        """导出经过公共脱敏处理的配置，不自动写文件或生成原值日志。"""
        with self._lock:
            self._require_open()
            values = {
                self._metadata[model].name: value.model_dump(mode="json")
                for model, value in self._configs.items()
            }
        return Sanitizer.sanitize_sensitive_data(values)

    def add_listener(self, listener: ConfigListener) -> None:
        """同步顺序通知；回调可读，不能回写或等待另一个配置写入，耗时工作应延后。"""
        with self._lock:
            self._require_open()
            if listener not in self._listeners:
                self._listeners.append(listener)

    def remove_listener(self, listener: ConfigListener) -> bool:
        with self._lock:
            if listener not in self._listeners:
                return False
            self._listeners.remove(listener)
            return True

    def replace_memory(self, values: Mapping[str, object]) -> ConfigUpdateResult:
        """用完整内存层替换旧层；空映射表示移除此层覆盖。"""
        with self._lock:
            self._require_reload(ConfigSourceEnum.MEMORY)
        flat = self._flatten(values)
        return self._commit(ConfigSourceEnum.MEMORY, (flat, dict.fromkeys(flat, "内存配置覆盖")))

    def reload_files(self) -> ConfigUpdateResult:
        """重新读取所有声明文件；任何读取或模型失败都保留旧层。"""
        with self._lock:
            self._require_reload(ConfigSourceEnum.FILE)
            revision = self._revision
        return self._commit(ConfigSourceEnum.FILE, self._read_files(), expected_revision=revision)

    async def refresh_external(self, loader: ConfigLoader) -> ConfigUpdateResult:
        """等待显式外部加载器，拒绝用迟到快照覆盖期间已经发布的新版本。"""
        with self._lock:
            self._require_reload(ConfigSourceEnum.EXTERNAL)
            revision = self._revision
        try:
            values = await loader()
        except Exception as error:
            raise BootstrapConfigError(f"外部配置加载失败（{type(error).__name__}）") from error
        flat = self._flatten(values)
        return self._commit(
            ConfigSourceEnum.EXTERNAL,
            (flat, dict.fromkeys(flat, "外部配置快照")),
            expected_revision=revision,
        )

    def close(self) -> None:
        """关闭刷新与读取，释放本应用的模型和监听引用。"""
        notification = self._notifying.get()
        if notification is not None and notification.active:
            raise BootstrapConfigError("配置监听器不能关闭正在通知的配置提供者")
        with self._updates_lock, self._lock:
            self._closed = True
            self._listeners.clear()
            self._configs.clear()
            self._origins.clear()
            self._layers.clear()
            self._environment_layers.clear()
            self._environment_trees.clear()

    def _commit(
        self,
        source: ConfigSourceEnum,
        layer: tuple[dict[str, object], dict[str, str]],
        *,
        expected_revision: int | None = None,
    ) -> ConfigUpdateResult:
        # 写入和同步通知串行；模型读取只使用 _lock，通知中仍能读取已提交值。
        with self._updates_lock:
            with self._lock:
                self._require_reload(source)
                if expected_revision is not None and expected_revision != self._revision:
                    raise BootstrapConfigError("外部配置加载期间版本已变化，拒绝迟到快照")
                if self._layers[source] == layer:
                    return ConfigUpdateResult(ConfigChange(self._revision, ()), ())
                layers = dict(self._layers)
                layers[source] = layer
                configs, origins = self._build(layers)
                changed = tuple(
                    sorted(
                        self._metadata[model].name
                        for model, value in configs.items()
                        if value != self._configs[model] or origins[model] != self._origins[model]
                    )
                )
                self._layers, self._configs, self._origins = layers, configs, origins
                self._revision += 1
                change = ConfigChange(self._revision, changed)
                listeners = tuple(self._listeners) if changed else ()
            return self._notify(change, listeners)

    def _notify(
        self, change: ConfigChange, listeners: tuple[ConfigListener, ...]
    ) -> ConfigUpdateResult:
        errors: list[BaseException] = []
        notification = ConfigNotification()
        token = self._notifying.set(notification)
        try:
            for listener in listeners:
                try:
                    result = listener(change)
                    if inspect.isawaitable(result):
                        if inspect.iscoroutine(result):
                            result.close()
                        raise TypeError("配置监听器必须同步完成")
                except BaseException as error:
                    errors.append(error)
        finally:
            notification.active = False
            self._notifying.reset(token)
        interruptions = [error for error in errors if not isinstance(error, Exception)]
        if interruptions:
            if len(errors) == 1:
                raise errors[0]
            raise BaseExceptionGroup("配置已提交，但变更通知被中断", errors)
        return ConfigUpdateResult(change, tuple(errors))

    def _build(
        self, layers: dict[ConfigSourceEnum, tuple[dict[str, object], dict[str, str]]]
    ) -> tuple[dict[type[BaseModel], BaseModel], dict[type[BaseModel], dict[str, str]]]:
        configs, all_origins = {}, {}
        trees = {source: ConfigValues.tree(layer[0]) for source, layer in layers.items()}
        for model, metadata in self._metadata.items():
            active = dict(layers)
            active[ConfigSourceEnum.ENVIRONMENT] = self._environment_layers[model]
            trees[ConfigSourceEnum.ENVIRONMENT] = self._environment_trees[model]
            prefix = f"config.models.{metadata.name}"
            order = self._options.source_order if metadata.sources is None else metadata.sources
            values, origins = {}, {}
            self._check_extra_fields(model, metadata, active)
            for field, info in model.model_fields.items():
                key = metadata.field_keys.get(field, f"{prefix}.{field}")
                for source in reversed(metadata.field_sources.get(field, order)):
                    _, source_names = active[source]
                    present, raw_value = ConfigValues.read(trees[source], key)
                    if not present:
                        continue
                    value = self._parse_collection(raw_value, info.annotation, field)
                    is_model = any(
                        isinstance(item, type) and issubclass(item, BaseModel)
                        for item in (info.annotation, *get_args(info.annotation))
                    )
                    if (
                        field in values
                        and is_model
                        and isinstance(values[field], dict)
                        and isinstance(value, dict)
                    ):
                        values[field] = ConfigValues.merge(values[field], value)
                    else:
                        values[field] = deepcopy(value)
                        origins = {
                            name: origin
                            for name, origin in origins.items()
                            if name != field and not name.startswith(field + ".")
                        }
                    for name in ConfigValues.sources(value, "", field):
                        source_key = key + name[len(field) :]
                        origins[name] = self._origin(source_names, source_key, source.value)
            try:
                configs[model] = model.model_validate(values, by_name=True)
            except ValidationError as error:
                fields = []
                for detail in error.errors(include_input=False, include_url=False):
                    field = ".".join(map(str, detail["loc"]))
                    fields.append(
                        f"{prefix}.{field}（来源：{self._origin(origins, field, '未提供')}，{detail['type']}）"
                    )
                raise BootstrapConfigError("配置模型校验失败：" + "；".join(fields)) from error
            all_origins[model] = origins
        return configs, all_origins

    def _model_environment(
        self, model: type[BaseModel], metadata: ConfigModelMetadata
    ) -> tuple[dict[str, object], dict[str, str]]:
        values, origins = self._bootstrap.get_model_environment(model, prefix=metadata.env_prefix)
        flat, source_names = {}, {}
        for field, value in values.items():
            key = metadata.field_keys.get(field, f"config.models.{metadata.name}.{field}")
            for name, nested in self._flatten({key: value}).items():
                flat[name] = nested
                field_path = field + name[len(key) :]
                source_names[name] = self._origin(
                    origins, field_path, f"环境变量 {metadata.env_prefix}{field.upper()}"
                )
        return flat, source_names

    def _read_files(self) -> tuple[dict[str, object], dict[str, str]]:
        if ConfigSourceEnum.FILE not in self._options.source_order:
            return {}, {}
        values, sources = {}, {}
        seen = set()
        for item in self._options.files:
            path = (self._bootstrap.base_dir / item.path).resolve()
            if path in seen:
                raise BootstrapConfigError(f"配置文件重复：{path}")
            seen.add(path)
            raw = ConfigFileReader.read(
                path, required=item.required, max_bytes=self._options.max_source_bytes
            )
            flat = self._flatten(raw)
            incoming_parents = ConfigValues.parents(flat)
            existing_parents = ConfigValues.parents(values)
            for key, value in flat.items():
                parent = key.rpartition(".")[0]
                while parent:
                    if parent in values and not isinstance(values[parent], Mapping):
                        values[parent] = {}
                        sources[parent] = str(path)
                    parent = parent.rpartition(".")[0]
                if key in existing_parents and (
                    not isinstance(value, Mapping) or key not in incoming_parents
                ):
                    for descendant in tuple(values):
                        if descendant.startswith(key + "."):
                            del values[descendant]
                            sources.pop(descendant, None)
                values[key] = value
            sources.update(dict.fromkeys(flat, str(path)))
        return values, sources

    def _flatten(self, values: Mapping[str, object]) -> dict[str, object]:
        if not isinstance(values, Mapping):
            raise BootstrapConfigError("配置源快照必须是字符串键映射")
        return ConfigValues.flatten(values, max_items=self._options.max_source_items)

    @staticmethod
    def _origin(sources: Mapping[str, str], key: str, missing: str) -> str:
        descendants = {source for name, source in sources.items() if name.startswith(key + ".")}
        if key not in sources and descendants:
            return "、".join(sorted(descendants))
        while key:
            if key in sources:
                return sources[key]
            key = key.rpartition(".")[0]
        return missing

    @staticmethod
    def _parse_collection(value: object, annotation: object, field: str) -> object:
        alternatives = get_args(annotation) if get_origin(annotation) in {Union, UnionType} else ()
        if value == "null" and type(None) in alternatives and str not in alternatives:
            return None
        containers = {list, tuple, set, frozenset, dict}
        collection = get_origin(annotation) in containers or any(
            get_origin(item) in containers for item in alternatives
        )
        if isinstance(value, str) and collection and str not in alternatives:
            try:
                return json.loads(value)
            except json.JSONDecodeError as error:
                raise BootstrapConfigError(f"配置集合字段必须使用 JSON：{field}") from error
        return value

    @classmethod
    def _validate_model(cls, model: type[BaseModel], seen: set[type]) -> None:
        if model in seen:
            return
        seen.add(model)
        model.model_rebuild()
        if (
            model.model_config.get("extra") != "forbid"
            or model.model_config.get("frozen") is not True
        ):
            raise BootstrapConfigError(
                f"配置模型必须 frozen=True 且 extra='forbid'：{model.__qualname__}"
            )
        for name, info in model.model_fields.items():
            if not info.is_required():
                raise BootstrapConfigError(
                    f"配置默认值只能放公共 YAML：{model.__qualname__}.{name}"
                )
            pending = [info.annotation]
            while pending:
                annotation = pending.pop()
                if isinstance(annotation, type) and issubclass(annotation, BaseModel):
                    cls._validate_model(annotation, seen)
                else:
                    pending.extend(get_args(annotation))

    @staticmethod
    def _check_extra_fields(
        model: type[BaseModel], metadata: ConfigModelMetadata, layers: dict
    ) -> None:
        prefix = f"config.models.{metadata.name}."
        for values, sources in layers.values():
            group = prefix[:-1]
            if group in values and not isinstance(values[group], Mapping):
                raise BootstrapConfigError(
                    f"配置模型分组必须是映射：{group}（来源：{ConfigProvider._origin(sources, group, '配置源')}）"
                )
            extras = {
                key[len(prefix) :].split(".")[0] for key in values if key.startswith(prefix)
            } - model.model_fields.keys()
            if extras:
                field = sorted(extras)[0]
                raise BootstrapConfigError(
                    f"配置模型未声明字段：{prefix}{field}（来源：{ConfigProvider._origin(sources, prefix + field, '配置源')}）"
                )

    def _require_open(self) -> None:
        if self._closed:
            raise BootstrapConfigError("配置提供者已关闭")

    def _require_reload(self, source: ConfigSourceEnum) -> None:
        self._require_open()
        notification = self._notifying.get()
        if notification is not None and notification.active:
            raise BootstrapConfigError("配置监听器不能重入配置写入")
        if not self._options.reload_enabled:
            raise BootstrapConfigError("配置刷新已由 config.reload_enabled 关闭")
        if source not in self._options.source_order:
            raise BootstrapConfigError(f"配置源未在 source_order 启用：{source.value}")
