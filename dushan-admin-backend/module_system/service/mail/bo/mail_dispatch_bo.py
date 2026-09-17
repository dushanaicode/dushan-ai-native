from typing import Any

from framework.common.schemas.base_bo import BaseBO


class MailDispatchBO(BaseBO):
    mail: str | None
    user_id: int
    user_type: int
    template_code: str
    template_params: dict[str, Any]
