from collections.abc import Callable, Mapping, Sequence
from typing import Any, TypeVar, cast

from sqlalchemy import Select, SQLColumnExpression, func, select
from sqlalchemy.ext.asyncio import AsyncSession

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
    """按实例配置处理内存与SQL分页，返回items/total。

    例如DataPaginator(settings).paginate_list(rows, PageQuery(page=2))。
    排序只使用服务端声明的字段到取值函数映射，不执行客户端表达式。
    SQL查询使用调用方的AsyncSession，不提交、回滚或关闭事务；跨查询一致性由事务隔离保证。
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

    async def paginate_query(
        self,
        session: AsyncSession,
        statement: Select[tuple[T]],
        page_query: PageQuery | None = None,
        *,
        sort_columns: Mapping[str, SQLColumnExpression[Any]] | None = None,
        order_by: Sequence[SQLColumnExpression[Any]] = (),
    ) -> PageResult[T]:
        """分页一个实体或标量查询；多列结果须由调用方先定义明确投影。

        调用方须提供稳定排序；客户端排序覆盖原order_by，可用order_by=(User.id,)
        追加唯一键作为同值排序依据。计数保留DISTINCT/GROUP BY，不做隐式实体去重。
        全量读取使用LIMIT上限+1探测实际超限，不只依赖预先COUNT。
        """
        if len(statement.column_descriptions) != 1:
            raise ValueError("SQL分页要求选择单个实体或标量")
        query = PageQuery() if page_query is None else page_query
        size = self._page_size(query)
        limit = self._fetch_all_limit(query)
        fields = self._sorting_fields(query, set(sort_columns or {}))
        base_query = statement.limit(None).offset(None)
        if fields:
            assert sort_columns is not None
            base_query = base_query.order_by(None).order_by(
                *(
                    sort_columns[field.field].desc()
                    if field.order == "desc"
                    else sort_columns[field.field].asc()
                    for field in fields
                )
            )
        if order_by:
            base_query = base_query.order_by(*order_by)
        total = cast(
            int,
            await session.scalar(
                select(func.count()).select_from(base_query.order_by(None).subquery())
            ),
        )
        if limit is not None:
            if total > limit:
                raise IllegalArgumentException(msg=f"全量查询最多允许 {limit} 条")
            records = list((await session.scalars(base_query.limit(limit + 1))).all())
            if len(records) > limit:
                raise IllegalArgumentException(msg=f"全量查询最多允许 {limit} 条")
            return PageResult(items=records, total=len(records))
        if total == 0:
            return PageResult.empty()
        records = list(
            (await session.scalars(base_query.limit(size).offset((query.page - 1) * size))).all()
        )
        return PageResult(items=records, total=total)

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
