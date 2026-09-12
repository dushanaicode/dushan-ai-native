import os
from collections.abc import Mapping
from copy import deepcopy
from pathlib import Path
from typing import TypeVar

import yaml
from pydantic import BaseModel, ValidationError

from framework.common.enums.application_environment_enum import ApplicationEnvironmentEnum
from framework.starter_config.provider.bootstrap_config_error import BootstrapConfigError
from framework.starter_config.provider.unique_key_loader import UniqueKeyLoader
from framework.starter_config.source.config_values import ConfigValues

Settings = TypeVar("Settings", bound=BaseModel)


class BootstrapConfigProvider:
    """读取显式配置并保留字段来源，配置模型不补运行默认值。

    公共 YAML 提供默认值，环境文件、非生产个人文件、环境变量依次覆盖。
    get_config 返回校验后的模型，get_sources 返回来源名称而不暴露配置值。
    例如 get_sources(ApplicationSettings)["log.console_level"] 可定位最后生效的来源。
    """

    def __init__(
        self,
        base_dir: Path,
        environment: ApplicationEnvironmentEnum,
        values: dict[str, object],
        environ: Mapping[str, str],
        sources: dict[str, str],
        loaded_files: tuple[str, ...],
    ) -> None:
        """保存当前加载快照，不与其他应用共享配置或来源状态。"""
        self.base_dir = base_dir
        self.environment = environment
        self._values = deepcopy(values)
        self._environ = dict(environ)
        self._sources = dict(sources)
        self._loaded_files = loaded_files

    @classmethod
    def load(
        cls,
        base_dir: str | Path,
        *,
        app_env: str | None = None,
        environ: Mapping[str, str] | None = None,
    ) -> "BootstrapConfigProvider":
        """合并显式文件并选定运行环境，生产环境不读取个人覆盖文件。"""
        if isinstance(base_dir, str) and not base_dir.strip():
            raise BootstrapConfigError("配置目录不能为空")
        root = Path(base_dir).resolve()
        process_env = dict(os.environ if environ is None else environ)
        values = cls._read_yaml(root / "application.yaml", required=True)
        sources = ConfigValues.sources(values, "application.yaml")
        loaded_files = ["application.yaml"]
        server = values.get("server", {})
        if not isinstance(server, dict):
            raise BootstrapConfigError("server 必须是配置分组（来源：application.yaml）")
        if app_env is not None:
            selected, environment_source = app_env, "启动参数 app_env/--env"
        elif "SERVER_ENV" in process_env:
            selected, environment_source = process_env["SERVER_ENV"], "环境变量 SERVER_ENV"
        elif "env" in server:
            selected, environment_source = server["env"], sources["server.env"]
        else:
            raise BootstrapConfigError(
                "缺少运行环境 server.env：请在 application.yaml、SERVER_ENV 或 --env 中明确提供"
            )
        try:
            environment = ApplicationEnvironmentEnum(str(selected).strip().lower())
        except ValueError:
            raise BootstrapConfigError(
                f"SERVER_ENV 无效（来源：{environment_source}），可选值为 dev、test、staging、prod"
            ) from None
        profile = f"application-{environment.value}.yaml"
        file_names = [profile]
        if environment != ApplicationEnvironmentEnum.PRODUCTION:
            file_names.append("application-local.yaml")
        for name in file_names:
            path = root / name
            override = cls._read_yaml(
                path,
                required=name == profile and environment == ApplicationEnvironmentEnum.PRODUCTION,
            )
            if path.exists():
                loaded_files.append(name)
            override_sources = ConfigValues.sources(override, name)
            values = ConfigValues.merge(values, override)
            sources.update(override_sources)
        server = values.setdefault("server", {})
        if not isinstance(server, dict):
            raise BootstrapConfigError(f"server 必须是配置分组（来源：{sources['server']}）")
        # 环境选择先于文件合并，后续文件不能切换已选定的环境。
        server["env"] = environment.value
        sources["server.env"] = environment_source
        return cls(root, environment, values, process_env, sources, tuple(loaded_files))

    @staticmethod
    def _read_yaml(path: Path, *, required: bool = False) -> dict[str, object]:
        """读取单文档 YAML，报告文件与位置但不回显配置原值。"""
        if not path.exists():
            if required:
                raise BootstrapConfigError(f"缺少配置文件：{path.name}")
            return {}
        try:
            with path.open(encoding="utf-8-sig") as stream:
                data = yaml.load(stream, Loader=UniqueKeyLoader)
        except BootstrapConfigError as error:
            raise BootstrapConfigError(f"{path.name}：{error}") from None
        except yaml.YAMLError as error:
            mark = getattr(error, "problem_mark", None)
            location = f"，第 {mark.line + 1} 行" if mark else ""
            raise BootstrapConfigError(f"配置文件格式错误：{path.name}{location}") from None
        except (OSError, UnicodeError):
            raise BootstrapConfigError(f"无法读取 UTF-8 配置文件：{path.name}") from None
        if data is None:
            return {}
        if not isinstance(data, dict):
            raise BootstrapConfigError(f"配置文件顶层必须是键值映射：{path.name}")
        if any(key.isupper() and "_" in key for key in data):
            raise BootstrapConfigError(f"{path.name} 不再接受大写平铺 YAML，请使用小写嵌套配置")
        return data

    @classmethod
    def _environment_keys(
        cls, model_type: type[BaseModel], prefix: str, path: str = ""
    ) -> dict[str, str]:
        """按模型声明列出环境变量名到字段路径的映射，不接受拼错的受管配置变量。

        字段 a_b 与嵌套字段 a.b 都会映射到 X_A_B；这种歧义是模型声明错误，
        无论环境里是否真的设置了该变量都直接拒绝，消息只含变量名和字段路径。
        """
        result: dict[str, str] = {}
        for name, info in model_type.model_fields.items():
            key = prefix + name.upper()
            field_path = f"{path}.{name}" if path else name
            if isinstance(info.annotation, type) and issubclass(info.annotation, BaseModel):
                nested = cls._environment_keys(info.annotation, key + "_", field_path)
            else:
                nested = {key: field_path}
            for variable, owner in nested.items():
                if variable in result:
                    raise BootstrapConfigError(
                        f"环境变量名歧义：{variable} 同时对应字段 {result[variable]} 与 {owner}"
                        f"（模型 {model_type.__qualname__}）"
                    )
                result[variable] = owner
        return result

    def _apply_environment(
        self,
        model_type: type[BaseModel],
        values: object,
        prefix: str,
        sources: dict[str, str],
        path: str,
    ):
        """仅用实际提供的环境变量覆盖字段，保留无效分组供模型明确报错。"""
        if not isinstance(values, dict):
            return values
        result = deepcopy(values)
        for field, info in model_type.model_fields.items():
            key = prefix + field.upper()
            field_path = f"{path}.{field}" if path else field
            if key == "SERVER_ENV":
                result[field] = self.environment.value
            elif isinstance(info.annotation, type) and issubclass(info.annotation, BaseModel):
                nested = self._apply_environment(
                    info.annotation, result.get(field, {}), key + "_", sources, field_path
                )
                if field in result or nested:
                    result[field] = nested
            elif key in self._environ:
                result[field] = self._environ[key]
                sources[field_path] = f"环境变量 {key}"
        return result

    def _resolve_input(self, settings_type: type[BaseModel], prefix: str):
        """准备同一份校验输入与来源快照，不写回原配置。"""
        group = prefix.rstrip("_").lower()
        values = self._values.get(group, {}) if prefix else self._values
        prefixes = (
            (prefix,)
            if prefix
            else tuple(name.upper() + "_" for name in settings_type.model_fields)
        )
        allowed = self._environment_keys(settings_type, prefix)
        unknown = sorted(
            key for key in self._environ if key.startswith(prefixes) and key not in allowed
        )
        if unknown:
            raise BootstrapConfigError("未声明的环境配置项：" + "、".join(unknown))
        sources = dict(self._sources)
        values = self._apply_environment(settings_type, values, prefix, sources, group)
        active_paths = ConfigValues.sources(values, "", group)
        return values, {key: sources[key] for key in active_paths if key in sources}

    def get_sources(self, settings_type: type[BaseModel], *, prefix: str = "") -> dict[str, str]:
        """返回字段最后生效的来源名称，不返回配置值或共享可变字典。"""
        _, sources = self._resolve_input(settings_type, prefix)
        return sources

    def get_yaml_snapshot(self) -> tuple[dict[str, object], dict[str, str]]:
        """为模型配置提供启动 YAML 的独立值/来源快照，不再次读取磁盘。"""
        return deepcopy(self._values), dict(self._sources)

    def get_group_prefixes(self) -> dict[str, str]:
        """启动配置各顶层分组占用的环境前缀，例如 log → LOG_；模型前缀不得与之重叠。"""
        return {f"{group.upper()}_": group for group in self._values}

    def get_model_environment(
        self, model: type[BaseModel], *, prefix: str
    ) -> tuple[dict[str, object], dict[str, str]]:
        """只提取指定模型的环境值，拒绝该前缀下的拼写错误。"""
        allowed = self._environment_keys(model, prefix)
        unknown = sorted(
            key for key in self._environ if key.startswith(prefix) and key not in allowed
        )
        if unknown:
            raise BootstrapConfigError("未声明的模型环境配置项：" + "、".join(unknown))
        sources: dict[str, str] = {}
        values = self._apply_environment(model, {}, prefix, sources, "")
        return values, sources

    def get_config(self, settings_type: type[Settings], *, prefix: str = "") -> Settings:
        """返回校验后的配置；缺项或无效值报告字段及来源，不补代码默认值。"""
        values, sources = self._resolve_input(settings_type, prefix)
        try:
            return settings_type.model_validate(values)
        except ValidationError as error:
            fields = []
            for detail in error.errors(include_input=False, include_url=False):
                parts = [prefix.rstrip("_").lower()] if prefix else []
                parts.extend(str(part) for part in detail["loc"])
                path = ".".join(parts)
                reason = detail.get("ctx", {}).get("error")
                if detail["type"] == "missing":
                    reason = "缺少必填配置项"
                elif detail["type"] == "extra_forbidden":
                    reason = "未声明的配置项"
                if reason is None:
                    reason = "值的类型或范围不合法"
                candidates = {
                    value
                    for key, value in sources.items()
                    if not path or key == path or key.startswith(path + ".")
                }
                parent = path
                while not candidates and "." in parent:
                    parent = parent.rsplit(".", 1)[0]
                    if parent in sources:
                        candidates.add(sources[parent])
                origin = (
                    "、".join(sorted(candidates))
                    if candidates
                    else "未提供；已读取 " + "、".join(self._loaded_files)
                )
                fields.append(f"{path or '整体配置'}（来源：{origin}）：{reason}")
            raise BootstrapConfigError("配置校验失败：" + "；".join(fields)) from None
