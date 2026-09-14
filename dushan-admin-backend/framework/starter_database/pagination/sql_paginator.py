from collections.abc import Mapping, Sequence
from typing import Any, TypeVar, cast

from sqlalchemy import Select, SQLColumnExpression, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from framework.common.exception.exceptions.illegal_argument_exception import (
    IllegalArgumentException,
)
from framework.common.page.core.data_paginator import DataPaginator
from framework.common.page.schemas.page_query import PageQuery
from framework.common.page.schemas.page_result import PageResult

T = TypeVar("T")


class SqlPaginator(DataPaginator):
    """复用公共分页限制执行 SQL，Session 与事务始终由调用方持有。"""

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
