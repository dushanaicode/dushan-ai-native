import re
from collections.abc import Callable
from typing import Any

from pydantic.alias_generators import to_camel, to_snake


class StrUtils:
    """处理文本、命名和列表解析；不吞掉转换失败。"""

    @staticmethod
    def find_all_between(content: str, start: str, end: str) -> list[str]:
        """提取成对分隔符中的文本，不执行分隔符中的正则。"""
        if not start or not end:
            raise ValueError("起止分隔符不能为空")
        return re.findall(f"{re.escape(start)}(.*?){re.escape(end)}", content, re.DOTALL)

    @staticmethod
    def remove_line_contains(content: str, keyword: str) -> str:
        """移除含有指定关键字的整行，输出统一使用换行符。"""
        if not keyword:
            raise ValueError("关键字不能为空")
        return "\n".join(line for line in content.splitlines() if keyword not in line)

    @staticmethod
    def sub_before(string: str, separator: str, include_separator: bool = False) -> str:
        """读取首个分隔符之前的内容，找不到时保留原字符串。"""
        head, found, _ = string.partition(separator)
        return head + found if include_separator else head

    @staticmethod
    def truncate(value: str, max_length: int, ellipsis: str = "...") -> str:
        """将总长度限制在 max_length 内，长度不足时截短省略符本身。"""
        if max_length < 0:
            raise ValueError("最大长度不能为负数")
        if len(value) <= max_length:
            return value
        suffix = ellipsis[:max_length]
        return value[: max_length - len(suffix)] + suffix

    @staticmethod
    def to_camel_case(value: str) -> str:
        """使用与模型别名相同的 Pydantic 驼峰规则。"""
        return to_camel(value)

    @staticmethod
    def to_snake_case(value: str) -> str:
        """将驼峰或连续大写缩写转换为蛇形命名。"""
        return to_snake(value)

    @classmethod
    def deep_transform_keys(cls, data: Any, transform_func: Callable[[str], str]) -> Any:
        """递归转换字典键，遇到转换后重名则报错，避免覆盖数据。"""
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                converted = transform_func(key) if isinstance(key, str) else key
                if converted in result:
                    raise ValueError("字典键转换后重名")
                result[converted] = cls.deep_transform_keys(value, transform_func)
            return result
        if isinstance(data, list):
            return [cls.deep_transform_keys(item, transform_func) for item in data]
        return data

    @staticmethod
    def to_list(value: str, separator: str = ",") -> list[str]:
        """按指定分隔符拆分并去除空白项。"""
        return [item.strip() for item in value.split(separator) if item.strip()]

    @classmethod
    def to_int_list(cls, value: str, separator: str = ",") -> list[int]:
        """将各项解析成整数，任何非法项都使本次解析失败。"""
        return [int(item) for item in cls.to_list(value, separator)]

    @classmethod
    def to_int_set(cls, value: str, separator: str = ",") -> set[int]:
        """解析整数并按集合语义去重。"""
        return set(cls.to_int_list(value, separator))

    @staticmethod
    def escape_like(value: str) -> str:
        """转义反斜杠、% 和 _；SQL 查询仍须参数绑定并指定 escape='\\\\'。"""
        return value.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")
