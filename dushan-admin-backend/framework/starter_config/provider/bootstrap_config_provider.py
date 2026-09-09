"""独立于数据库、容器和模块扫描的启动配置读取。"""

import os
from collections.abc import Mapping
from copy import deepcopy
from pathlib import Path
from typing import TypeVar

import yaml
from pydantic import BaseModel, ValidationError

from framework.common.enums.application_environment_enum import ApplicationEnvironmentEnum

Settings = TypeVar("Settings", bound=BaseModel)


class BootstrapConfigError(ValueError):
    """向启动入口报告不包含配置原值的配置错误。"""


class _UniqueKeyLoader(yaml.SafeLoader):
    """拒绝重复键，避免配置被无声覆盖。"""

    def construct_mapping(self, node, deep=False):
        result = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str):
                raise BootstrapConfigError("配置键必须是字符串")
            if key in result:
                raise BootstrapConfigError(f"配置键重复：{key}")
            result[key] = self.construct_object(value_node, deep=deep)
        return result


class BootstrapConfigProvider:
    """持有一次配置快照，应用之间不共享可变缓存。"""

    def __init__(
        self,
        base_dir: Path,
        environment: ApplicationEnvironmentEnum,
        values: dict[str, object],
        environ: Mapping[str, str],
    ) -> None:
        self.base_dir = base_dir
        self.environment = environment
        self._values = deepcopy(values)
        self._environ = dict(environ)

    @classmethod
    def load(
        cls,
        base_dir: str | Path,
        *,
        app_env: str | None = None,
        environ: Mapping[str, str] | None = None,
    ) -> "BootstrapConfigProvider":
        """按基础、环境、本地覆盖顺序读取配置；生产环境不读本地覆盖。"""
        root = Path(base_dir).resolve()
        process_env = dict(os.environ if environ is None else environ)
        values = cls._read_yaml(root / "application.yaml", required=True)
        server = values.get("server", {})
        if not isinstance(server, dict):
            raise BootstrapConfigError("server 必须是配置分组")
        selected = (
            app_env
            if app_env is not None
            else process_env.get("SERVER_ENV", server.get("env", "dev"))
        )
        try:
            environment = ApplicationEnvironmentEnum(str(selected).strip().lower())
        except ValueError:
            raise BootstrapConfigError(
                "SERVER_ENV 无效，可选值为 dev、test、staging、prod"
            ) from None
        values = cls._merge(
            values,
            cls._read_yaml(
                root / f"application-{environment.value}.yaml",
                required=environment == ApplicationEnvironmentEnum.PRODUCTION,
            ),
        )
        if environment != ApplicationEnvironmentEnum.PRODUCTION:
            values = cls._merge(values, cls._read_yaml(root / "application-local.yaml"))
        # 已选择的环境不允许再被覆盖文件改写。
        server = values.setdefault("server", {})
        if not isinstance(server, dict):
            raise BootstrapConfigError("server 必须是配置分组")
        server["env"] = environment.value
        return cls(root, environment, values, process_env)

    @classmethod
    def _merge(cls, base: dict, override: dict) -> dict:
        """配置分组递归合并，列表与普通值整体覆盖，不修改输入快照。"""
        result = deepcopy(base)
        for key, value in override.items():
            if isinstance(value, dict) and isinstance(result.get(key), dict):
                result[key] = cls._merge(result[key], value)
            else:
                result[key] = deepcopy(value)
        return result

    @staticmethod
    def _read_yaml(path: Path, *, required: bool = False) -> dict[str, object]:
        """读取单文档嵌套配置，错误信息不输出 YAML 原文。"""
        if not path.exists():
            if required:
                raise BootstrapConfigError(f"缺少配置文件：{path.name}")
            return {}
        try:
            with path.open(encoding="utf-8-sig") as stream:
                data = yaml.load(stream, Loader=_UniqueKeyLoader)
        except BootstrapConfigError:
            raise
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
            raise BootstrapConfigError(
                f"{path.name} 不再接受大写平铺 YAML，请改为小写嵌套配置，例如 server.port；"
                "进程环境变量名称保持不变"
            )
        return data

    def _apply_environment(self, model_type: type[BaseModel], values: object, prefix: str):
        """沿模型层级覆盖环境变量，保留未知字段和错误结构交给模型报错。"""
        if not isinstance(values, dict):
            return values
        result = deepcopy(values)
        for field, info in model_type.model_fields.items():
            key = prefix + field.upper()
            if key == "SERVER_ENV":
                result[field] = self.environment.value
            elif isinstance(info.annotation, type) and issubclass(info.annotation, BaseModel):
                nested = self._apply_environment(info.annotation, result.get(field, {}), key + "_")
                if field in result or nested:
                    result[field] = nested
            elif key in self._environ:
                result[field] = self._environ[key]
        return result

    def get_config(self, settings_type: type[Settings], *, prefix: str = "") -> Settings:
        """校验完整配置；提供 prefix 时也可读取对应分组，环境变量命名不变。"""
        values = self._values.get(prefix.rstrip("_").lower(), {}) if prefix else self._values
        values = self._apply_environment(settings_type, values, prefix)
        try:
            return settings_type.model_validate(values)
        except ValidationError as error:
            fields = []
            for detail in error.errors(include_input=False, include_url=False):
                location = ".".join(str(part) for part in detail["loc"]) or "整体配置"
                reason = detail.get("ctx", {}).get("error")
                if detail["type"] == "extra_forbidden":
                    reason = "未声明的配置项"
                fields.append(
                    f"{location}：{reason}" if reason else f"{location}：值的类型或范围不合法"
                )
            raise BootstrapConfigError("配置校验失败：" + "；".join(fields)) from None
