from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from module_system.api.dept.dept_api_impl import DeptApiImpl
from module_system.api.user.user_profile_api_impl import UserProfileApiImpl
from module_system.dal.dataobject.user.admin_user_do import AdminUserDO


class TestUserProfileApiFailureContracts:
    @pytest.fixture
    def api(self):
        """注入纯内存依赖，禁止画像测试访问外部服务。"""
        api = UserProfileApiImpl()
        api.admin_user_service = SimpleNamespace(
            get_user=AsyncMock(
                return_value=AdminUserDO(id=10, nickname="用户", dept_id=20, post_ids=[30])
            )
        )
        api.user_profile_service = SimpleNamespace(get_user_profile=AsyncMock(return_value=None))
        api.dept_api = SimpleNamespace(
            get_dept=AsyncMock(return_value=SimpleNamespace(name="研发部"))
        )
        api.post_api = SimpleNamespace(
            get_post_list=AsyncMock(return_value=[SimpleNamespace(name="工程师")])
        )
        return api

    async def test_missing_user_returns_none(self, api):
        """用户不存在时直接返回空值，不查询画像或关联资料。"""
        api.admin_user_service.get_user.return_value = None

        assert await api.get_user_profile_for_ai(10) is None

        api.user_profile_service.get_user_profile.assert_not_awaited()
        api.dept_api.get_dept.assert_not_awaited()
        api.post_api.get_post_list.assert_not_awaited()

    @pytest.mark.parametrize("post_ids", [None, []])
    async def test_absent_associations_remain_empty(self, api, post_ids):
        """未配置部门和岗位时保留明确空值，不调用关联查询。"""
        user = api.admin_user_service.get_user.return_value
        user.dept_id = None
        user.post_ids = post_ids

        result = await api.get_user_profile_for_ai(10)

        assert result.user_id == 10
        assert result.dept_name is None
        assert result.post_names == []
        assert result.work_scope is None
        api.dept_api.get_dept.assert_not_awaited()
        api.post_api.get_post_list.assert_not_awaited()

    async def test_success_preserves_profile_and_associations(self, api):
        """有效画像与关联资料按原契约聚合返回。"""
        api.user_profile_service.get_user_profile.return_value = SimpleNamespace(
            work_scope="架构设计",
            expertise="后端",
            communication_style="简洁",
            ai_preference={"responseStyle": "concise"},
            skills=["Python"],
        )

        result = await api.get_user_profile_for_ai(10)

        assert result.model_dump() == {
            "user_id": 10,
            "nickname": "用户",
            "dept_name": "研发部",
            "post_names": ["工程师"],
            "work_scope": "架构设计",
            "expertise": "后端",
            "communication_style": "简洁",
            "ai_preference": {"responseStyle": "concise"},
            "skills": ["Python"],
        }
        api.dept_api.get_dept.assert_awaited_once_with(20)
        api.post_api.get_post_list.assert_awaited_once_with([30])

    @pytest.mark.parametrize("dependency", ["dept", "post"])
    @pytest.mark.parametrize("error_type", [RuntimeError, TypeError])
    async def test_association_failures_propagate(self, api, dependency, error_type):
        """关联查询故障和编程错误原样传播，不能生成伪正常画像。"""
        error = error_type("关联查询失败")
        query = api.dept_api.get_dept if dependency == "dept" else api.post_api.get_post_list
        query.side_effect = error

        with pytest.raises(error_type) as captured:
            await api.get_user_profile_for_ai(10)

        assert captured.value is error

    async def test_deleted_department_follows_non_nullable_dept_api_contract(self, api):
        """已配置部门不存在时保留部门 API 的校验错误，不解释为无关联。"""
        dept_api = DeptApiImpl()
        dept_api.dept_service = SimpleNamespace(get_dept=AsyncMock(return_value=None))
        api.dept_api = dept_api

        with pytest.raises(ValidationError):
            await api.get_user_profile_for_ai(10)
