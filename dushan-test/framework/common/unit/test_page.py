from operator import itemgetter

import pytest
from pydantic import ValidationError

from fixtures.config_factory import ConfigFactory
from framework.common.exception.exceptions.illegal_argument_exception import (
    IllegalArgumentException,
)
from framework.common.page.config.page_settings import PageSettings
from framework.common.page.core.data_paginator import DataPaginator
from framework.common.page.schemas.page_query import PageQuery
from framework.common.page.schemas.page_result import PageResult
from framework.common.page.schemas.sortable_page_query import SortablePageQuery
from framework.common.schemas.base_vo import BaseVO

pytestmark = pytest.mark.unit


def test_page_uses_instance_defaults_and_preserves_total_on_an_empty_page():
    """省略大小时使用应用配置，超出末页仍保留已知总数。"""
    paginator = DataPaginator(ConfigFactory.build(PageSettings, "page", default_size=2, max_size=3))
    items = [1, 2, 3, 4, 5]
    assert paginator.paginate_list(items, PageQuery(page="2")).to_response() == {
        "items": [3, 4],
        "total": 5,
    }
    assert paginator.paginate_list(items, PageQuery(page=4)).to_response() == {
        "items": [],
        "total": 5,
    }
    assert (
        len(DataPaginator(ConfigFactory.build(PageSettings, "page")).paginate_list(items).items)
        == 5
    )
    assert items == [1, 2, 3, 4, 5]
    with pytest.raises(IllegalArgumentException, match="最大为 3"):
        paginator.paginate_list(items, PageQuery(page_size=4))


@pytest.mark.parametrize(
    "payload",
    [
        {"page": 0},
        {"page": True},
        {"pageSize": 0},
        {"pageSize": False},
        {"pageSize": 1.5},
        {"pageSize": float("inf")},
        {"pageSize": float("nan")},
        {"fetchAll": True},
        {"_fetch_all": True},
    ],
)
def test_page_rejects_invalid_or_private_request_fields(payload):
    """请求不能绕过正整数边界，也不能开启服务端私有全量状态。"""
    with pytest.raises(ValidationError):
        PageQuery.model_validate(payload)


def test_fetch_all_requires_platform_and_endpoint_permission_and_enforces_limits():
    """平台开关与接口声明必须同时满足，接口只能收紧平台上限。"""
    query = PageQuery().enable_fetch_all(max_rows=2)
    assert query.to_response() == {"page": 1, "pageSize": None}
    with pytest.raises(IllegalArgumentException, match="未启用"):
        DataPaginator(ConfigFactory.build(PageSettings, "page")).paginate_list([1], query)
    paginator = DataPaginator(
        ConfigFactory.build(PageSettings, "page", fetch_all_enabled=True, fetch_all_max_rows=3)
    )
    assert paginator.paginate_list([1, 2], query).items == [1, 2]
    with pytest.raises(IllegalArgumentException, match="最多允许 2 条"):
        paginator.paginate_list([1, 2, 3], query)
    with pytest.raises(IllegalArgumentException, match="平台上限"):
        paginator.paginate_list([], PageQuery().enable_fetch_all(max_rows=4))
    with pytest.raises(IllegalArgumentException, match="最多允许 3 条"):
        paginator.paginate_list([1, 2, 3, 4], PageQuery().enable_fetch_all())


@pytest.mark.parametrize("limit", [0, -1, True, "3", 2.5, float("inf"), float("nan")])
def test_fetch_all_endpoint_limit_is_a_real_positive_integer(limit):
    """内部调用不能通过类型转换意外取消全量限制。"""
    with pytest.raises(ValueError, match="正整数"):
        PageQuery().enable_fetch_all(max_rows=limit)


def test_sorting_is_whitelisted_stable_and_happens_before_pagination():
    """多字段优先级、稳定性与分页次序保持一致，不修改调用方集合。"""
    items = [
        {"id": 1, "group": "b", "score": 1},
        {"id": 2, "group": "a", "score": 2},
        {"id": 3, "group": "a", "score": 3},
        {"id": 4, "group": "a", "score": 3},
    ]
    query = SortablePageQuery(
        pageSize=3, sortingFields=[{"field": "group"}, {"field": "score", "order": "desc"}]
    )
    result = DataPaginator(ConfigFactory.build(PageSettings, "page")).paginate_list(
        items, query, sort_keys={"group": itemgetter("group"), "score": itemgetter("score")}
    )
    assert [item["id"] for item in result.items] == [3, 4, 2]
    assert result.total == 4
    assert [item["id"] for item in items] == [1, 2, 3, 4]


@pytest.mark.parametrize(
    "fields,maximum",
    [
        ([{"field": "allowed"}, {"field": "private"}], 5),
        ([{"field": "allowed"}, {"field": "allowed"}], 5),
        ([{"field": "allowed"}], 0),
    ],
)
def test_sort_policy_is_checked_before_any_getter_executes(fields, maximum):
    """越权字段、重复字段和关闭排序时在读取数据前失败。"""
    calls = []
    query = SortablePageQuery(sortingFields=fields)
    with pytest.raises(IllegalArgumentException):
        DataPaginator(
            ConfigFactory.build(PageSettings, "page", max_sort_fields=maximum)
        ).paginate_list([1], query, sort_keys={"allowed": lambda item: calls.append(item)})
    assert calls == []


def test_result_conversion_keeps_concrete_model_fields_and_json_aliases():
    """泛型转换不能把目标模型当成空 BaseModel，响应字段必须真实保留。"""

    class RowVO(BaseVO):
        record_id: int

    class Row:
        record_id = 7
        password = "private"

    result = PageResult(items=[Row()], total=4).convert(RowVO)
    assert result.to_response() == {"items": [{"recordId": 7}], "total": 4}
    assert result.map(lambda item: item.record_id).items == [7]
    assert PageResult.empty(total=4).to_response() == {"items": [], "total": 4}
    with pytest.raises(ValidationError):
        PageResult(items=[], total=-1)


@pytest.mark.parametrize(
    "values",
    [
        {"max_size": 5},
        {"default_size": False},
        {"fetch_all_max_rows": 0},
        {"max_sort_fields": -1},
        {"max_size": float("inf")},
        {"unknown": 1},
    ],
)
def test_page_configuration_rejects_invalid_boundaries(values):
    """错误配置在应用创建时失败，避免请求运行时才发现限制失效。"""
    with pytest.raises(ValidationError):
        ConfigFactory.build(PageSettings, "page", **values)
