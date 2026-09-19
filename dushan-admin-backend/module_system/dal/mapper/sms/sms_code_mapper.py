from __future__ import annotations

from sqlalchemy import select

from framework.starter_database.public import (
    BaseMapper,
)
from framework.starter_di.public import (
    mapper,
)
from module_system.dal.dataobject.sms.sms_code_do import SmsCodeDO


@mapper()
class SmsCodeMapper(BaseMapper[SmsCodeDO]):
    def __init__(self):
        super().__init__(SmsCodeDO)

    async def select_last_by_mobile(
        self, mobile: str, code: str | None, scene: int | None
    ) -> SmsCodeDO | None:
        stmt = select(SmsCodeDO).where(SmsCodeDO.mobile == mobile)
        if scene is not None:
            stmt = stmt.where(SmsCodeDO.scene == scene)
        if code is not None:
            stmt = stmt.where(SmsCodeDO.code == code)
        stmt = stmt.order_by(SmsCodeDO.id.desc()).limit(1)
        result = await self.read(stmt)
        return result.scalar_one_or_none()
