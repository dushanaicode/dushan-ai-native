from framework.common.schemas import BaseBO


class MailSendResultBO(BaseBO):
    log_id: int
    message_id: str | None
    exception: Exception | None = None
