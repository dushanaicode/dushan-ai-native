from datetime import datetime
from unittest.mock import Mock, call

import pytest
from pydantic import ValidationError

from framework.common.enums import StatusEnum
from module_system.controller.admin.user.vo.user.user_import_excel_vo import UserImportExcelVO
from module_system.convert.user.user_convert import UserConvert
from module_system.dal.dataobject.dept.dept_do import DeptDO
from module_system.dal.dataobject.user.admin_user_do import AdminUserDO
from module_system.definitions.enums.common.common_sex_enum import CommonSexEnum


@pytest.fixture
def user():
    """提供含完整响应字段的用户实体，避免依赖数据库默认值。"""
    return AdminUserDO(
        id=1024,
        username="fixture",
        nickname="用户昵称",
        remark="备注",
        dept_id=2048,
        post_ids=[4096],
        email="fixture@example.com",
        mobile="13800138000",
        sex=CommonSexEnum.FEMALE.code,
        avatar="https://example.com/avatar.png",
        status=StatusEnum.ENABLE.code,
        login_ip="127.0.0.1",
        login_date=datetime(2026, 10, 6, 10, 30),
        create_time=datetime(2026, 10, 5, 9, 0),
        password="不得进入响应",
    )


@pytest.mark.parametrize("has_dept", [False, True])
def test_user_response_preserves_fields_and_optional_department(user, has_dept):
    """详情与列表转换保留响应合同，仅补充部门名称。"""
    dept = DeptDO(id=2048, name="研发部") if has_dept else None

    result = UserConvert.convert(user, dept)

    assert result.model_dump(by_alias=False) == {
        "id": "1024",
        "username": "fixture",
        "nickname": "用户昵称",
        "remark": "备注",
        "dept_id": "2048",
        "dept_name": "研发部" if has_dept else None,
        "post_ids": ["4096"],
        "email": "fixture@example.com",
        "mobile": "13800138000",
        "sex": CommonSexEnum.FEMALE.code,
        "avatar": "https://example.com/avatar.png",
        "status": StatusEnum.ENABLE.code,
        "login_ip": "127.0.0.1",
        "login_date": datetime(2026, 10, 6, 10, 30),
        "create_time": datetime(2026, 10, 5, 9, 0),
    }


def test_user_response_keeps_model_validation(user):
    """实体转换继续执行响应模型的归一化和字段校验。"""
    user.email = ""
    assert UserConvert.convert(user, None).email is None
    user.email = "不是邮箱"
    with pytest.raises(ValidationError):
        UserConvert.convert(user, None)


def test_simple_user_list_handles_missing_departments_with_one_lookup(user):
    """简表保留缺失部门语义，每个用户只查询一次部门映射。"""
    dept_map = Mock(wraps={2048: DeptDO(id=2048, name="研发部")})
    missing_dept_user = AdminUserDO(id=1025, nickname="部门已删除", dept_id=2049)
    no_dept_user = AdminUserDO(id=1026, nickname="未分配部门", dept_id=None)

    result = UserConvert.convert_simple_list([user, missing_dept_user, no_dept_user], dept_map)

    assert [vo.to_response() for vo in result] == [
        {"id": "1024", "nickname": "用户昵称", "deptId": "2048", "deptName": "研发部"},
        {"id": "1025", "nickname": "部门已删除", "deptId": "2049", "deptName": None},
        {"id": "1026", "nickname": "未分配部门", "deptId": None, "deptName": None},
    ]
    assert dept_map.get.call_args_list == [call(2048), call(2049), call(None)]
    assert UserConvert.convert_simple_list([], {}) == []


@pytest.mark.parametrize("dept_id", [None, "9223372036854775807"])
def test_import_to_save_preserves_department_id_and_full_row_fields(dept_id):
    """导入保存边界保留完整行与部门编号，不向保存请求透传导入状态。"""
    row = UserImportExcelVO(
        username="fixture",
        nickname="导入昵称",
        dept_id=dept_id,
        status=StatusEnum.DISABLE.code,
    )

    result = UserConvert.convert_import_to_save_vo(row, "Initial123!")

    assert result.dept_id == (None if dept_id is None else int(dept_id))
    assert row.dept_id == result.dept_id
    assert result.password == "Initial123!"
    assert result.username == "fixture"
    assert result.nickname == "导入昵称"
    assert result.email is None
    assert result.mobile is None
    assert result.sex is None
    assert result.model_fields_set == {
        "username",
        "nickname",
        "dept_id",
        "email",
        "mobile",
        "sex",
        "password",
    }


@pytest.mark.parametrize(
    ("fields", "password"),
    [({"username": "bad!"}, "Initial123!"), ({"nickname": "名" * 31}, "Initial123!"), ({}, "x")],
)
def test_import_to_save_keeps_save_request_validation(fields, password):
    """导入转换继续拒绝不符合保存请求约束的账号、昵称和密码。"""
    row = UserImportExcelVO(**{"username": "fixture", "nickname": "导入昵称", **fields})

    with pytest.raises(ValidationError):
        UserConvert.convert_import_to_save_vo(row, password)
