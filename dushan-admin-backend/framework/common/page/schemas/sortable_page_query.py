from framework.common.page.schemas.page_query import PageQuery
from framework.common.page.schemas.sort_field import SortField


class SortablePageQuery(PageQuery):
    """携带有先后优先级的排序字段，第一项优先级最高。"""

    sorting_fields: tuple[SortField, ...] = ()
