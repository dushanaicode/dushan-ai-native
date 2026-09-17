from typing import Any

from framework.common.schemas.base_bo import BaseBO


class MailBatchSendBO(BaseBO):
    to_mails: list[str]
    cc_mails: list[str] | None
    bcc_mails: list[str] | None
    user_id: int
    template_code: str
    template_params: dict[str, Any]
