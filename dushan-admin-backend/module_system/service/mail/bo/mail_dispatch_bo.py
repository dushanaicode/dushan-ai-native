from typing import Any

from framework.common.schemas import BaseBO


class MailDispatchBO(BaseBO):
    require_delivery: bool = False
    mail: str | None
    user_id: int
    user_type: int
    template_code: str
    template_params: dict[str, Any]
