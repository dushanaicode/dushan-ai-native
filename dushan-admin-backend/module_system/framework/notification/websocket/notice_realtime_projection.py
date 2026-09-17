from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.inject import Inject
from framework.starter_security.context.security_context import SecurityContext
from module_system.dal.mapper.notification.notice_message_mapper import (
    NoticeMessageMapper,
)


@service
class NoticeRealtimeProjection:
    messages: NoticeMessageMapper = Inject()
    security: SecurityContext = Inject()

    async def project(self, payload, context):
        entry = await self.messages.select_by_id(int(payload.message_id))
        if entry is None or entry.user_id != int(self.security.require().account_id):
            return None
        return payload
