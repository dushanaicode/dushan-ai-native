from __future__ import annotations

from typing import Collection, Protocol, runtime_checkable

from module_system.api.user.dto.admin_user_resp_dto import AdminUserRespDTO


@runtime_checkable
class AdminUserApi(Protocol):
    """Admin 用户 API 接口"""

    async def get_user(self, id: int) -> AdminUserRespDTO | None:
        """通过用户 ID 查询用户"""
        ...

    async def get_user_list_by_subordinate(self, id: int) -> list[AdminUserRespDTO]:
        """通过用户 ID 查询用户下属"""
        ...

    async def get_user_list(self, ids: Collection[int]) -> list[AdminUserRespDTO]:
        """通过用户 ID 查询用户们"""
        ...

    async def get_user_list_by_dept_ids(self, dept_ids: Collection[int]) -> list[AdminUserRespDTO]:
        """获得指定部门的用户数组"""
        ...

    async def get_user_list_by_post_ids(self, post_ids: Collection[int]) -> list[AdminUserRespDTO]:
        """获得指定岗位的用户数组"""
        ...

    async def get_user_map(self, ids: Collection[int]) -> dict[int, AdminUserRespDTO]:
        """获得用户 Map"""
        ...

    async def validate_user(self, id: int) -> None:
        """校验用户是否有效"""
        ...

    async def validate_user_list(self, ids: Collection[int]) -> None:
        """校验用户们是否有效"""
        ...

    async def check_user_exists(self, user_id: int) -> bool:
        """检查用户是否存在"""
        ...

    async def get_user_nickname(self, user_id: int) -> str | None:
        """获取用户昵称"""
        ...

    async def search_users(self, keyword: str, limit: int = 20) -> list[AdminUserRespDTO]:
        """按关键字搜索用户（昵称/手机号模糊匹配）"""
        ...
