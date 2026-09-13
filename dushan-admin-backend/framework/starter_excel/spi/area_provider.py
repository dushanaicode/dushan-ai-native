from typing import Protocol, TypeVar

AreaT_co = TypeVar("AreaT_co", covariant=True)


class AreaProvider(Protocol[AreaT_co]):
    """地区显示与反向解析的最小边界；地区对象由提供方定义和持有。"""

    def format_area_path(self, area_id: int, separator: str = "/") -> str | None: ...

    def parse_area_path(self, path_str: str, separator: str = "/") -> AreaT_co | None: ...
