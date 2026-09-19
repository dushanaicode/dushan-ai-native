from __future__ import annotations

from typing import Protocol, runtime_checkable

from framework.common.enums import UserTypeEnum
from framework.starter_security.public import (
    LoginSession,
)
from module_system.controller.admin.user.vo.profile.profile_online_device_vo import (
    ProfileOnlineDeviceVO,
)
from module_system.controller.admin.user.vo.profile.profile_update_req_vo import (
    UserProfileUpdateReqVO,
)
from module_system.dal.dataobject.user.admin_user_profile_do import AdminUserProfileDO


@runtime_checkable
class UserProfileService(Protocol):
    async def get_user_profile(self, user_id: int) -> AdminUserProfileDO | None: ...

    async def create_or_update_profile(
        self, user_id: int, req_vo: UserProfileUpdateReqVO
    ) -> None: ...

    async def get_user_online_devices(
        self, session: LoginSession, user_type: UserTypeEnum
    ) -> list[ProfileOnlineDeviceVO]: ...

    async def kickout_online_device(self, token_id: int, current_user_id: int) -> None: ...
