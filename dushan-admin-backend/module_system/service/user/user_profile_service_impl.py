from __future__ import annotations

from datetime import datetime, timezone
from typing import override

from framework.common.datetime.core.date_utils import DateUtils
from framework.common.enums.user_type_enum import UserTypeEnum
from framework.common.exception.exceptions.service_exception import ServiceException
from framework.starter_database.decorators.transactional import transactional
from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.inject import Inject
from framework.starter_security.model.login_session import LoginSession
from module_system.controller.admin.user.vo.profile.profile_online_device_vo import (
    ProfileOnlineDeviceVO,
)
from module_system.controller.admin.user.vo.profile.profile_update_req_vo import (
    UserProfileUpdateReqVO,
)
from module_system.convert.user.user_convert import UserConvert
from module_system.dal.dataobject.user.admin_user_profile_do import AdminUserProfileDO
from module_system.dal.mapper.oauth2.oauth2_access_token_mapper import OAuth2AccessTokenMapper
from module_system.dal.mapper.user.admin_user_profile_mapper import AdminUserProfileMapper
from module_system.definitions.constants.error_code_constants import ErrorCodeConstants
from module_system.service.auth.auth_admin_auth_service import AuthAdminAuthService
from module_system.service.oauth2.oauth2_token_service import OAuth2TokenService
from module_system.service.user.user_profile_service import UserProfileService


@service(interface=UserProfileService)
class UserProfileServiceImpl(UserProfileService):
    admin_user_profile_mapper: AdminUserProfileMapper = Inject()
    oauth2_token_service: OAuth2TokenService = Inject()
    admin_auth_service: AuthAdminAuthService = Inject()
    date_utils: DateUtils = Inject()

    @override
    async def get_user_profile(self, user_id: int) -> AdminUserProfileDO | None:
        return await self.admin_user_profile_mapper.select_by_user_id(user_id)

    @override
    @transactional
    async def create_or_update_profile(self, user_id: int, req_vo: UserProfileUpdateReqVO) -> None:
        profile_do = UserConvert.convert_update_req_to_user_profile(user_id, req_vo)
        if not profile_do:
            return
        existing_profile = await self.get_user_profile(user_id)
        if existing_profile:
            profile_do.id = existing_profile.id
            await self.admin_user_profile_mapper.update_by_id(profile_do)
        else:
            await self.admin_user_profile_mapper.insert(profile_do)

    tokens: OAuth2AccessTokenMapper = Inject()

    async def get_user_online_devices(
        self, session: LoginSession, user_type: UserTypeEnum
    ) -> list[ProfileOnlineDeviceVO]:
        rows = await self.oauth2_token_service.get_access_tokens_by_user_id(
            int(session.account_id), user_type.code
        )
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        digest = session.token_digest
        devices = []
        for row in sorted(rows, key=lambda item: item.create_time, reverse=True):
            info = row.user_info
            devices.append(
                ProfileOnlineDeviceVO(
                    token_id=str(row.id),
                    device_name=info.get("user_agent"),
                    ip_address=info.get("ipaddr"),
                    login_location=info.get("login_location"),
                    browser=info.get("browser"),
                    os=info.get("os"),
                    login_time=row.create_time,
                    online=not row.revoked and row.expires_time > now,
                    is_current=row.token_digest == digest,
                )
            )
        return devices

    async def kickout_online_device(self, token_id: int, current_user_id: int) -> None:
        token = await self.tokens.select_by_id(token_id)
        if token is None or token.user_id != current_user_id:
            raise ServiceException(ErrorCodeConstants.USER_KICKOUT_DEVICE_NOT_OWNER)
        await self.oauth2_token_service.remove_access_token_batch([token.id])
