from framework.common.schemas.base_bo import BaseBO


class MailSendResultBO(BaseBO):
    log_id: int
    message_id: str | None
    exception: Exception | None = None
