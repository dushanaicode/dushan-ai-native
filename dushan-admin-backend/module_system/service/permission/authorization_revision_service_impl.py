from __future__ import annotations

from sqlalchemy import update

from framework.starter_database.session.session_provider import SessionProvider
from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.inject import Inject
from module_system.dal.dataobject.permission.authorization_revision_do import (
    AuthorizationRevisionDO,
)
from module_system.service.permission.authorization_revision_service import (
    AuthorizationRevisionService,
)


@service(interface=AuthorizationRevisionService)
class AuthorizationRevisionServiceImpl(AuthorizationRevisionService):
    database: SessionProvider = Inject()

    async def advance(self):
        # ponytail: 全局版本使所有租户缓存一起失效；权限写入量增大时再按租户拆版本行。
        async with self.database.transaction() as session:
            result = await session.execute(
                update(AuthorizationRevisionDO)
                .where(AuthorizationRevisionDO.id == 1)
                .values(revision=AuthorizationRevisionDO.revision + 1)
            )
            if result.rowcount != 1:
                raise ValueError("缺少系统授权版本初始行")
