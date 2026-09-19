from typing import Any

from framework.common.schemas import BaseBO


class SmsSendBO(BaseBO):
    mobile: str | None
    user_id: int | None
    template_code: str
    template_params: dict[str, Any]
