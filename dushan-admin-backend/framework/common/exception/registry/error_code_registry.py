from collections.abc import Iterable
from inspect import getmembers_static

from framework.common.exception.core.error_code import ErrorCode
from framework.common.exception.exceptions.configuration_exception import ConfigurationException


class ErrorCodeRegistry:
    """在构造时校验错误码目录，运行期只提供实例查询。

    用 ErrorCodeRegistry([GlobalErrorCodeConstants, BusinessCodes]) 构建目录；
    应用持有自己的实例，扫描器只向装配层提供常量类集合。
    公开的 ErrorCode 属性按静态查找收集，包括继承属性，不执行描述符。
    重复编号抛出 ConfigurationException；全部收集成功后才保存结果。
    查询集合返回副本，目录不提供追加、清空或重置入口。
    """

    def __init__(self, source_classes: Iterable[type]) -> None:
        """一次构建完整目录，冲突时报告双方的模块、类名和属性名。"""
        entries: dict[int, tuple[str, str, ErrorCode]] = {}
        for source_class in source_classes:
            source_name = f"{source_class.__module__}.{source_class.__qualname__}"
            for name, value in getmembers_static(source_class):
                if name.startswith("_") or not isinstance(value, ErrorCode):
                    continue
                existing = entries.get(value.code)
                if existing is not None:
                    raise ConfigurationException(
                        msg=(
                            f"错误码冲突: {value.code} 被 {existing[0]}.{existing[1]} "
                            f"和 {source_name}.{name} 同时使用"
                        )
                    )
                entries[value.code] = (source_name, name, value)
        self._registry = entries

    def get_by_code(self, code: int) -> ErrorCode | None:
        """按编号查找错误码定义，未知编号返回 None。"""
        entry = self._registry.get(code)
        return entry[2] if entry is not None else None

    def get_all(self) -> dict[int, ErrorCode]:
        """返回已注册错误码的映射副本。"""
        return {code: entry[2] for code, entry in self._registry.items()}

    def get_all_detail(self) -> dict[int, tuple[str, str, ErrorCode]]:
        """返回完整来源类名、属性名与错误码组成的映射副本。"""
        return dict(self._registry)
