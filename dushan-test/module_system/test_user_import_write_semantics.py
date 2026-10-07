from inspect import unwrap
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from pydantic import SecretStr

from framework.common.enums import BuiltinTypeEnum, StatusEnum
from framework.common.exception import ServiceException
from module_system.controller.admin.user.vo.user.user_import_excel_vo import UserImportExcelVO
from module_system.controller.admin.user.vo.user.user_save_req_vo import UserSaveReqVO
from module_system.dal.dataobject.notification.notice_do import NoticeDO
from module_system.dal.dataobject.user.admin_user_do import AdminUserDO
from module_system.service.notification.notice_service_impl import NoticeServiceImpl
from module_system.service.user.admin_user_service_impl import AdminUserServiceImpl


@pytest.mark.parametrize("existing", [False, True])
@pytest.mark.parametrize("status", [None, StatusEnum.ENABLE.code, StatusEnum.DISABLE.code])
@pytest.mark.parametrize("dept_id", [None, "123456789012345678"])
async def test_user_import_preserves_full_row_fields_and_password(existing, status, dept_id):
    """导入新增和更新均保留整行字段、部门编号及原有密码语义。"""
    service = AdminUserServiceImpl()
    service.revisions = SimpleNamespace(advance=AsyncMock())
    service.settings = SimpleNamespace(default_password=SecretStr("Initial123!"))
    service.tenant = SimpleNamespace(get_required_tenant_id=Mock(return_value="1"))
    service.access_policy = SimpleNamespace(
        protect_owner_account=Mock(), is_owner=Mock(return_value=False)
    )
    service._validate_user_for_create_or_update = AsyncMock()
    service._encode_password = AsyncMock(return_value="encoded")
    old_user = AdminUserDO(id=10, username="fixture") if existing else None
    service.user_mapper = SimpleNamespace(
        select_by_username=AsyncMock(return_value=old_user),
        insert=AsyncMock(),
        update_by_id=AsyncMock(),
    )
    row = UserImportExcelVO(username="fixture", nickname="导入昵称", status=status, dept_id=dept_id)

    result = await unwrap(AdminUserServiceImpl.import_user_list)(service, [row], True)

    assert result.failure_usernames == {}
    write = service.user_mapper.update_by_id if existing else service.user_mapper.insert
    entity = write.await_args.args[0]
    assert entity.username == "fixture"
    assert entity.nickname == "导入昵称"
    assert "dept_id" in vars(entity)
    assert entity.dept_id == (None if dept_id is None else int(dept_id))
    assert (
        service._validate_user_for_create_or_update.await_args.kwargs["dept_id"] == entity.dept_id
    )
    for field in ("email", "mobile", "sex"):
        assert field in vars(entity)
        assert getattr(entity, field) is None
    if existing:
        assert entity.id == 10
        assert "password" not in vars(entity)
        assert "post_ids" not in vars(entity)
        assert ("status" in vars(entity)) == (status is not None)
        assert result.update_usernames == ["fixture"]
        service._encode_password.assert_not_awaited()
    else:
        assert entity.password == "encoded"
        assert entity.post_ids == []
        assert entity.status == (StatusEnum.ENABLE.code if status is None else status)
        assert result.create_usernames == ["fixture"]
    if status is not None:
        assert entity.status == status


async def test_user_create_does_not_validate_an_existing_user():
    service = AdminUserServiceImpl()
    service.revisions = SimpleNamespace(advance=AsyncMock())
    service.tenant_service = SimpleNamespace(get_current_tenant=AsyncMock())
    service._check_account_count = AsyncMock()
    service._validate_user_exists = AsyncMock(side_effect=AssertionError("新增不得查询已有用户"))
    for method in (
        "_validate_username_unique",
        "_validate_email_unique",
        "_validate_mobile_unique",
        "_validate_dept_list",
        "_validate_post_list",
    ):
        setattr(service, method, AsyncMock())
    service._encode_password = AsyncMock(return_value="encoded")
    service.user_mapper = SimpleNamespace(insert=AsyncMock())
    service.permission_cache = SimpleNamespace(invalidate_user_caches=AsyncMock())
    service.security_settings = SimpleNamespace(bizlog_enabled=False)

    await unwrap(AdminUserServiceImpl.create_user)(
        service, UserSaveReqVO(username="fixture", nickname="新增用户", password="Initial123!")
    )

    service._validate_user_exists.assert_not_awaited()
    service.user_mapper.insert.assert_awaited_once()
    service._validate_username_unique.assert_awaited_once_with(None, "fixture")


async def test_notice_validation_returns_entity_and_rejects_missing_or_builtin():
    service = NoticeServiceImpl()
    notice = NoticeDO(id=10, builtin=BuiltinTypeEnum.CUSTOM.code)
    service.notice_mapper = SimpleNamespace(select_by_id=AsyncMock(return_value=notice))
    assert await service._validate_for_update(10) is notice

    service.notice_mapper.select_by_id.return_value = None
    with pytest.raises(ServiceException):
        await service._validate_for_update(10)
    with pytest.raises(ServiceException):
        await service._validate_for_update(None)

    notice.builtin = BuiltinTypeEnum.BUILTIN.code
    service.notice_mapper.select_by_id.return_value = notice
    with pytest.raises(ServiceException):
        await service._validate_for_update(10)
