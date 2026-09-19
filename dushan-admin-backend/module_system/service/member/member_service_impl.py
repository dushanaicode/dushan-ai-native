from __future__ import annotations

from typing import override

from framework.common.exception import (
    GlobalErrorCodeConstants,
    ServiceException,
)
from framework.starter_di.public import (
    service,
)
from module_system.service.member.member_service import MemberService


@service(interface=MemberService)
class MemberServiceImpl(MemberService):
    """会员模块未接入时明确报告不可用。"""

    @override
    async def get_member_user_mobile(self, id: int) -> str | None:
        raise ServiceException(GlobalErrorCodeConstants.SERVICE_UNAVAILABLE, msg="会员模块尚未接入")

    @override
    async def get_member_user_email(self, id: int) -> str | None:
        raise ServiceException(GlobalErrorCodeConstants.SERVICE_UNAVAILABLE, msg="会员模块尚未接入")
