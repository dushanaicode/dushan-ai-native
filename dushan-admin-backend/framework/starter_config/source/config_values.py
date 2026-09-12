from collections.abc import Mapping
from copy import deepcopy

from framework.starter_config.provider.bootstrap_config_error import BootstrapConfigError


class ConfigValues:
    """统一配置树、点分键与来源；分组只存标记，叶子只复制一次。"""

    @classmethod
    def flatten(cls, values: Mapping[str, object], *, max_items: int) -> dict[str, object]:
        result: dict[str, object] = {}
        cls._walk(values, "", set(), result, max_items)
        for key in result:
            parent = key.rpartition(".")[0]
            while parent:
                if parent in result and not isinstance(result[parent], Mapping):
                    raise BootstrapConfigError(f"配置路径的父节点不是映射：{key}")
                parent = parent.rpartition(".")[0]
        return result

    @staticmethod
    def read(values: Mapping[str, object], key: str) -> tuple[bool, object]:
        """从已构建的内部配置树读取；进入模型前由调用方隔离可变值。"""
        value = values
        for part in key.split("."):
            if not isinstance(value, Mapping) or part not in value:
                return False, None
            value = value[part]
        return True, value

    @staticmethod
    def tree(values: Mapping[str, object]) -> dict[str, object]:
        """每层只建一次查询树，保留空映射和标量覆盖，不再按字段扫描全部键。"""
        result = {}
        for key in sorted(values, key=lambda name: (name.count("."), name)):
            parts = key.split(".")
            target = result
            for part in parts[:-1]:
                target = target.setdefault(part, {})
            value = values[key]
            target[parts[-1]] = {} if isinstance(value, Mapping) else value
        return result

    @staticmethod
    def parents(paths) -> set[str]:
        result = set()
        for path in paths:
            parent = path.rpartition(".")[0]
            while parent:
                result.add(parent)
                parent = parent.rpartition(".")[0]
        return result

    @staticmethod
    def merge(base: dict, override: dict) -> dict:
        """独立复制基础树后覆盖，避免每深入一层又复制整个基础子树。"""
        result = deepcopy(base)
        pending = [(result, override)]
        while pending:
            target, incoming = pending.pop()
            for key, value in incoming.items():
                if isinstance(value, dict) and isinstance(target.get(key), dict):
                    pending.append((target[key], value))
                else:
                    target[key] = deepcopy(value)
        return result

    @staticmethod
    def sources(values: object, source: str, path: str = "") -> dict[str, str]:
        result = {}
        pending = [(path, values, frozenset())]
        while pending:
            name, value, ancestors = pending.pop()
            if name:
                result[name] = source
            if isinstance(value, dict):
                if id(value) in ancestors:
                    raise BootstrapConfigError("配置输入不能包含循环引用")
                lineage = ancestors | {id(value)}
                pending.extend(
                    (f"{name}.{key}" if name else key, item, lineage) for key, item in value.items()
                )
        return result

    @classmethod
    def _walk(
        cls,
        values: Mapping[str, object],
        prefix: str,
        parents: set[int],
        result: dict[str, object],
        limit: int,
    ) -> None:
        parents.add(id(values))
        pending = [(iter(values.items()), prefix, id(values))]
        while pending:
            items, prefix, identity = pending[-1]
            try:
                key, value = next(items)
            except StopIteration:
                pending.pop()
                parents.remove(identity)
                continue
            if (
                not isinstance(key, str)
                or not key
                or any(not part or part != part.strip() for part in key.split("."))
            ):
                raise BootstrapConfigError("配置键必须是非空点分字符串")
            path = f"{prefix}.{key}" if prefix else key
            if path in result:
                raise BootstrapConfigError(f"配置路径重复：{path}")
            if len(result) >= limit:
                raise BootstrapConfigError("配置项数量超过已配置上限")
            result[path] = {} if isinstance(value, Mapping) else deepcopy(value)
            if isinstance(value, Mapping):
                if id(value) in parents:
                    raise BootstrapConfigError("配置输入不能包含循环引用")
                parents.add(id(value))
                pending.append((iter(value.items()), path, id(value)))
