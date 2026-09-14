from collections.abc import Callable, Mapping, Sequence
from typing import Any, TypeVar

from framework.common.exception.exceptions.illegal_argument_exception import (
    IllegalArgumentException,
)
from framework.common.page.config.page_settings import PageSettings
from framework.common.page.schemas.page_query import PageQuery
from framework.common.page.schemas.page_result import PageResult
from framework.common.page.schemas.sort_field import SortField
from framework.common.page.schemas.sortable_page_query import SortablePageQuery

T = TypeVar("T")


class DataPaginator:
    """按实例配置处理内存分页，并提供共用的分页限制，返回items/total。

    例如DataPaginator(settings).paginate_list(rows, PageQuery(page=2))。
    排序只使用服务端声明的字段到取值函数映射，不执行客户端表达式。
    数据库分页器复用本类的页大小、排序白名单和全量读取限制。
    """

    def __init__(self, settings: PageSettings) -> None:
        """保存当前应用的不可变分页配置。"""
        self.settings = settings

    def paginate_list(
        self,
        items: Sequence[T],
        page_query: PageQuery | None = None,
        *,
        sort_keys: Mapping[str, Callable[[T], Any]] | None = None,
    ) -> PageResult[T]:
        """先检查参数与读取上限，再排序和切片，保持原始序列不变。"""
        query = PageQuery() if page_query is None else page_query
        size = self._page_size(query)
        total = len(items)
        limit = self._fetch_all_limit(query)
        if limit is not None:
            if total > limit:
                raise IllegalArgumentException(msg=f"全量查询最多允许 {limit} 条")
            ordered = self._sort(items, query, sort_keys)
            return PageResult(items=list(ordered), total=total)
        ordered = self._sort(items, query, sort_keys)
        offset = (query.page - 1) * size
        return PageResult(items=list(ordered[offset : offset + size]), total=total)

    def _page_size(self, query: PageQuery) -> int:
        """解析当前应用的有效页大小，并检查普通分页上限。"""
        size = self.settings.default_size if query.page_size is None else query.page_size
        if size > self.settings.max_size:
            raise IllegalArgumentException(msg=f"pageSize 最大为 {self.settings.max_size}")
        return size

    def _fetch_all_limit(self, query: PageQuery) -> int | None:
        """验证服务端全量开关与接口上限，普通分页返回None。"""
        if not query.fetch_all:
            return None
        if not self.settings.fetch_all_enabled:
            raise IllegalArgumentException(msg="当前分页配置未启用全量查询")
        limit = self.settings.fetch_all_max_rows
        if query.fetch_all_max_rows is not None:
            if query.fetch_all_max_rows > limit:
                raise IllegalArgumentException(msg="接口全量上限不能超过平台上限")
            limit = query.fetch_all_max_rows
        return limit

    def _sorting_fields(self, query: PageQuery, allowed: set[str]) -> tuple[SortField, ...]:
        """在执行内存取值或SQL前完整校验排序数量、重复与白名单。"""
        if not isinstance(query, SortablePageQuery):
            return ()
        fields = query.sorting_fields
        if len(fields) > self.settings.max_sort_fields:
            raise IllegalArgumentException(msg="排序字段数量超过配置上限")
        if len({field.field for field in fields}) != len(fields):
            raise IllegalArgumentException(msg="排序字段不能重复")
        if any(field.field not in allowed for field in fields):
            raise IllegalArgumentException(msg="排序字段不在允许范围内")
        return fields

    def _sort(
        self,
        items: Sequence[T],
        query: PageQuery,
        sort_keys: Mapping[str, Callable[[T], Any]] | None,
    ) -> Sequence[T]:
        """验证完整排序白名单后执行稳定排序，取值函数须返回可比较的数据。"""
        fields = self._sorting_fields(query, set(sort_keys or {}))
        if not fields:
            return items
        assert sort_keys is not None
        ordered = items
        for field in reversed(fields):
            ordered = sorted(ordered, key=sort_keys[field.field], reverse=field.order == "desc")
        return ordered
