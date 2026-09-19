from typing import Any

from framework.common.schemas import BaseBO


class MailSendBO(BaseBO):
    mail: str | None
    user_id: int
    template_code: str
    template_params: dict[str, Any]
