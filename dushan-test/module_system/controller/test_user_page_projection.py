from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from fixtures.config_factory import ConfigFactory
from framework.common.page import PageResult, PageSettings
from framework.starter_database.ddl.ddl_cli import DdlCli
from framework.starter_excel.config.excel_settings import ExcelSettings
from framework.starter_excel.public import ExcelWriter
from module_system.controller.admin.user.user_controller import UserController
from module_system.controller.admin.user.vo.user.user_export_req_vo import UserExportReqVO
from module_system.controller.admin.user.vo.user.user_page_req_vo import UserPageReqVO
from module_system.controller.admin.user.vo.user.user_resp_vo import UserRespVO
from module_system.dal.dataobject.dept.dept_do import DeptDO
from module_system.dal.dataobject.user.admin_user_do import AdminUserDO

DdlCli._import_models("module_system")
DdlCli._import_models("module_infra")

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("has_rows,total", [(True, 23), (False, 23), (False, 0)])
async def test_user_page_preserves_total_and_optional_departments(has_rows, total):
    """用户分页保持查询总数、顺序及已删除部门的空值。"""
    users = (
        [
            AdminUserDO(
                id=user_id,
                username=f"user{user_id}",
                nickname=f"用户{user_id}",
                dept_id=dept_id,
                status=1,
                login_ip="127.0.0.1",
            )
            for user_id, dept_id in [(1024, 2048), (1025, 2049), (1026, None)]
        ]
        if has_rows
        else []
    )
    source = PageResult(items=users, total=total)
    service = SimpleNamespace(get_user_page=AsyncMock(return_value=source))
    departments = SimpleNamespace(
        get_dept_map=AsyncMock(return_value={2048: DeptDO(id=2048, name="研发部")})
    )
    query = UserPageReqVO(page=3)

    result = await UserController.get_user_page(query, service, departments)

    service.get_user_page.assert_awaited_once_with(query)
    departments.get_dept_map.assert_awaited_once_with([2048, 2049] if has_rows else [])
    assert result.data.total == total
    assert [item.id for item in result.data.items] == (["1024", "1025", "1026"] if has_rows else [])
    assert [item.dept_name for item in result.data.items] == (
        ["研发部", None, None] if has_rows else []
    )
    assert source.items == users and source.total == total


async def test_user_export_preserves_order_and_department_projection():
    """导出沿用列表转换，保留部门名称、空关联和选择的字段。"""
    users = [
        AdminUserDO(
            id=user_id,
            username=f"user{user_id}",
            nickname=f"用户{user_id}",
            dept_id=dept_id,
            status=1,
            login_ip="127.0.0.1",
        )
        for user_id, dept_id in [(1024, 2048), (1025, 2049)]
    ]
    service = SimpleNamespace(
        get_user_page=AsyncMock(return_value=PageResult(items=users, total=2))
    )
    departments = SimpleNamespace(
        get_dept_map=AsyncMock(return_value={2048: DeptDO(id=2048, name="研发部")})
    )
    writer = ExcelWriter(
        ExcelSettings.model_validate(
            {**ConfigFactory.values()["config"]["models"]["excel"], "max_export_rows": 11}
        ),
        ConfigFactory.build(PageSettings, "page", fetch_all_max_rows=7),
    )
    writer.write = AsyncMock(return_value=b"xlsx")
    files = SimpleNamespace(excel_stream=Mock())
    query = UserExportReqVO(fields=["nickname", "dept_name"])
    posts = SimpleNamespace(names=AsyncMock(return_value={}))

    response = await UserController.export_user_list(
        query, service, departments, writer, files, posts
    )

    service.get_user_page.assert_awaited_once_with(query)
    departments.get_dept_map.assert_awaited_once_with([2048, 2049])
    assert query.fetch_all and query.fetch_all_max_rows == 7
    sheet, model, rows = writer.write.call_args.args
    assert sheet == "数据" and model is UserRespVO
    assert [(row.id, row.nickname, row.dept_name) for row in rows] == [
        ("1024", "用户1024", "研发部"),
        ("1025", "用户1025", None),
    ]
    assert writer.write.call_args.kwargs["fields"] == query.fields
    assert writer.write.call_args.kwargs["providers"].posts is posts
    files.excel_stream.assert_called_once_with(b"xlsx", file_name="用户数据.xlsx")
    assert response is files.excel_stream.return_value
