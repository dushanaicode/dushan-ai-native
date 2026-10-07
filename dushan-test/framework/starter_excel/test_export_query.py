import pytest

from fixtures.config_factory import ConfigFactory
from framework.common.exception.exceptions.illegal_argument_exception import (
    IllegalArgumentException,
)
from framework.common.page.config.page_settings import PageSettings
from framework.common.page.core.data_paginator import DataPaginator
from framework.common.page.schemas.page_query import PageQuery
from framework.starter_excel.config.excel_settings import ExcelSettings
from framework.starter_excel.writer.excel_writer import ExcelWriter

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("excel_limit,page_limit", [(3, 5), (5, 3), (3, 3)])
def test_export_query_uses_both_limits_and_rejects_excess_rows(excel_limit, page_limit):
    """导出读取完整结果，但不能超出 Excel 或分页任一侧的上限。"""
    pages = ConfigFactory.build(
        PageSettings, "page", fetch_all_enabled=True, fetch_all_max_rows=page_limit
    )
    writer = ExcelWriter(
        ExcelSettings.model_validate(
            {**ConfigFactory.values()["config"]["models"]["excel"], "max_export_rows": excel_limit}
        ),
        pages,
    )
    query = PageQuery(page=2, page_size=1)
    writer.prepare_export_query(query)
    paginator = DataPaginator(pages)

    result = paginator.paginate_list([1, 2, 3], query)

    assert result.items == [1, 2, 3] and result.total == 3
    assert query.page == 2 and query.page_size == 1
    with pytest.raises(IllegalArgumentException, match="全量查询最多允许 3 条"):
        paginator.paginate_list([1, 2, 3, 4], query)


def test_export_query_keeps_platform_fetch_all_switch():
    """框架准备导出查询后，平台关闭全量读取时仍由分页器拒绝。"""
    pages = ConfigFactory.build(PageSettings, "page", fetch_all_enabled=False)
    writer = ExcelWriter(
        ExcelSettings.model_validate(ConfigFactory.values()["config"]["models"]["excel"]), pages
    )
    query = PageQuery()
    writer.prepare_export_query(query)

    with pytest.raises(IllegalArgumentException, match="当前分页配置未启用全量查询"):
        DataPaginator(pages).paginate_list([], query)
