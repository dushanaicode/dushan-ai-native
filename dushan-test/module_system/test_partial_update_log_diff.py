from inspect import unwrap
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from framework.starter_di.public import ApplicationContext
from framework.starter_security.bizlog.diff_renderer import DiffRenderer
from module_system.controller.admin.permission.vo.role.role_save_req_vo import RoleSaveReqVO
from module_system.controller.admin.user.vo.user.user_save_req_vo import UserSaveReqVO
from module_system.dal.dataobject.permission.role_do import RoleDO
from module_system.dal.dataobject.user.admin_user_do import AdminUserDO
from module_system.service.permission.role_service_impl import RoleServiceImpl
from module_system.service.user.admin_user_service_impl import AdminUserServiceImpl


class TestPartialUpdateLogDiff:
    @pytest.mark.parametrize("changes", [{}, {"remark": None}, {"remark": "新备注"}])
    async def test_user_log_matches_submitted_fields(self, monkeypatch, changes):
        """未提交字段保留旧值，显式清空和修改仍记录真实差异。"""
        user = AdminUserDO(
            id=10,
            username="fixture",
            nickname="原昵称",
            remark="旧备注",
            dept_id=20,
            post_ids=[30],
            email="fixture@example.com",
            mobile="13800138000",
            sex=1,
            avatar="https://example.com/avatar.png",
        )
        service = AdminUserServiceImpl()
        service.access_policy = SimpleNamespace(protect_owner_account=Mock())
        service.tenant = SimpleNamespace(get_required_tenant_id=Mock(return_value="1"))
        service.revisions = SimpleNamespace(advance=AsyncMock())
        service.security_settings = SimpleNamespace(
            bizlog_enabled=True, bizlog_max_diff_items=20, bizlog_max_length=2000
        )
        service.log_context = SimpleNamespace(put=Mock())
        service._validate_user_exists = AsyncMock(return_value=user)
        service._validate_user_for_create_or_update = AsyncMock()
        service.permission_cache = SimpleNamespace(invalidate_user_caches=AsyncMock())
        service._update_user_post = AsyncMock()
        service._dept_label = AsyncMock(return_value="研发部")
        service._post_label = AsyncMock(return_value="工程师")
        log_service = SimpleNamespace(record_diff=AsyncMock())
        monkeypatch.setattr(ApplicationContext, "lookup", Mock(return_value=log_service))

        async def update(entity):
            for field, value in vars(entity).items():
                if field != "_sa_instance_state":
                    setattr(user, field, value)
            return user

        service.user_mapper = SimpleNamespace(update_by_id=AsyncMock(side_effect=update))
        request = UserSaveReqVO(id="10", username="fixture", nickname="新昵称", **changes)
        await unwrap(AdminUserServiceImpl.update_user)(service, request)

        before, after = log_service.record_diff.await_args.args
        renderer = DiffRenderer(
            service.security_settings, **log_service.record_diff.await_args.kwargs
        )
        expected = "用户昵称: 原昵称 → 新昵称"
        if "remark" in changes:
            expected += f"；备注: 旧备注 → {changes['remark']}"
        assert await renderer.render(before, after) == expected
        assert before.nickname == "原昵称"
        assert after.remark == user.remark == changes.get("remark", "旧备注")
        assert after.dept_id == user.dept_id == 20
        assert after.post_ids == user.post_ids == [30]
        assert after.email == user.email == "fixture@example.com"
        assert after.mobile == user.mobile == "13800138000"
        assert after.sex == user.sex == 1
        assert after.avatar == user.avatar == "https://example.com/avatar.png"
        service._update_user_post.assert_not_awaited()
        service.permission_cache.invalidate_user_caches.assert_not_awaited()

    @pytest.mark.parametrize("changes", [{}, {"remark": None}, {"remark": "新备注"}])
    async def test_role_log_and_write_match_submitted_fields(self, monkeypatch, changes):
        """角色省略备注时日志与写入均保留旧值，显式空值仍生效。"""
        role = RoleDO(id=10, name="原角色", code="fixture", sort=1, remark="旧备注")
        service = RoleServiceImpl()
        service.revisions = SimpleNamespace(advance=AsyncMock())
        service.database = SimpleNamespace(after_commit=Mock())
        service.security_settings = SimpleNamespace(
            bizlog_enabled=True, bizlog_max_diff_items=20, bizlog_max_length=2000
        )
        service.log_context = SimpleNamespace(put=Mock())
        service.validate_role_for_update = AsyncMock(return_value=role)
        service.validate_role_duplicate = AsyncMock()
        service.permission_cache = SimpleNamespace(invalidate_role_caches=AsyncMock())
        log_service = SimpleNamespace(record_diff=AsyncMock())
        monkeypatch.setattr(ApplicationContext, "lookup", Mock(return_value=log_service))

        async def update(entity):
            for field, value in vars(entity).items():
                if field != "_sa_instance_state":
                    setattr(role, field, value)
            return role

        service.role_mapper = SimpleNamespace(update_by_id=AsyncMock(side_effect=update))
        request = RoleSaveReqVO(id="10", name="新角色", code="fixture", sort=1, **changes)
        await unwrap(RoleServiceImpl.update_role)(service, request)

        before, after = log_service.record_diff.await_args.args
        expected = "角色名称: 原角色 → 新角色"
        if "remark" in changes:
            expected += f"；备注: 旧备注 → {changes['remark']}"
        assert await DiffRenderer(service.security_settings).render(before, after) == expected
        assert before.name == "原角色"
        assert after.remark == role.remark == changes.get("remark", "旧备注")
        written = service.role_mapper.update_by_id.await_args.args[0]
        assert ("remark" in vars(written)) == ("remark" in changes)
