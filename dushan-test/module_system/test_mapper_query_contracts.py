from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, Mock

import pytest

from framework.starter_database.ddl.ddl_dialects import DdlDialects
from module_system.controller.admin.announcement.vo.announcement_page_req_vo import (
    AnnouncementPageReqVO,
)
from module_system.controller.admin.notification.vo.notice.notice_page_req_vo import NoticePageReqVO
from module_system.controller.admin.tenant.vo.tenant.tenant_page_req_vo import TenantPageReqVO
from module_system.dal.dataobject.announcement.announcement_do import AnnouncementDO
from module_system.dal.mapper.announcement.announcement_mapper import AnnouncementMapper
from module_system.dal.mapper.notification.notice_mapper import NoticeMapper
from module_system.dal.mapper.tenant.tenant_mapper import TenantMapper

FILTERS = [
    (AnnouncementMapper, AnnouncementPageReqVO, "title"),
    (TenantMapper, TenantPageReqVO, "name"),
    (TenantMapper, TenantPageReqVO, "contact_name"),
    (TenantMapper, TenantPageReqVO, "contact_mobile"),
    (NoticeMapper, NoticePageReqVO, "title"),
    (NoticeMapper, NoticePageReqVO, "publisher"),
]


@pytest.mark.parametrize("mapper_type, vo_type, field", FILTERS)
@pytest.mark.parametrize(
    "value, escaped",
    [
        ("AbC", "AbC"),
        ("50%", r"50\%"),
        ("a_b", r"a\_b"),
        (r"A\B%_", r"A\\B\%\_"),
    ],
)
@pytest.mark.parametrize("dialect_name", DdlDialects.names())
async def test_literal_contains_compiles_without_user_wildcards(
    monkeypatch, mapper_type, vo_type, field, value, escaped, dialect_name
):
    """六个字段在七库均转义字面通配符，并编译为忽略大小写的包含查询。"""
    mapper = mapper_type()
    page = object()
    paginate = AsyncMock(return_value=page)
    monkeypatch.setattr(mapper, "paginate_query", paginate)
    request = vo_type(**{field: value})

    assert await mapper.select_page(request) is page

    statement, actual_request = paginate.call_args.args
    assert actual_request is request
    compiled = statement.whereclause.compile(dialect=DdlDialects.resolve(dialect_name))
    assert list(compiled.params.values()) == [escaped]
    sql = str(compiled).lower()
    assert field in sql
    assert " escape " in sql
    assert "\\" in sql
    assert "ilike" in sql or ("lower(" in sql and " like " in sql)
    assert "%" in sql


@pytest.mark.parametrize("mapper_type, vo_type, field", FILTERS)
@pytest.mark.parametrize("value", [None, ""])
async def test_optional_contains_preserves_empty_value_policy(
    monkeypatch, mapper_type, vo_type, field, value
):
    """维持原可选筛选合同：仅发布人空串形成匹配全部非空发布人的条件。"""
    mapper = mapper_type()
    paginate = AsyncMock()
    monkeypatch.setattr(mapper, "paginate_query", paginate)

    await mapper.select_page(vo_type(**{field: value}))

    statement, _ = paginate.call_args.args
    if field == "publisher" and value == "":
        assert list(statement.whereclause.compile().params.values()) == [""]
    else:
        assert statement.whereclause is None


@pytest.mark.parametrize("dialect_name", DdlDialects.names())
@pytest.mark.parametrize("found", [False, True])
async def test_announcement_lock_uses_public_execute_and_write_scope(
    monkeypatch, dialect_name, found
):
    """公告锁查询经公开入口进入写会话，保留主键条件、排他锁和缺失语义。"""
    mapper = AnnouncementMapper()
    announcement = AnnouncementDO(id=73) if found else None
    result = Mock()
    result.scalar_one_or_none.return_value = announcement
    session_execute = AsyncMock(return_value=result)
    session = Mock(execute=session_execute)
    writes = []

    @asynccontextmanager
    async def session_scope(*, for_write):
        """记录公开执行入口选择的会话用途，不连接数据库。"""
        writes.append(for_write)
        yield session

    monkeypatch.setattr(mapper, "_get_session_scope", session_scope)
    execute = AsyncMock(wraps=mapper.execute)
    monkeypatch.setattr(mapper, "execute", execute)

    assert await mapper.select_for_update(73) is announcement

    execute.assert_awaited_once()
    (statement,) = execute.call_args.args
    session_execute.assert_awaited_once_with(statement, None)
    result.scalar_one_or_none.assert_called_once_with()
    assert writes == [True]
    compiled = statement.compile(dialect=DdlDialects.resolve(dialect_name))
    assert compiled.params == {"id_1": 73}
    assert "FOR UPDATE" in str(compiled)
    assert not statement._for_update_arg.read
    assert not statement._for_update_arg.nowait
    assert not statement._for_update_arg.skip_locked
