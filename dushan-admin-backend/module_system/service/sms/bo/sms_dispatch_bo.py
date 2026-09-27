from typing import Any

from framework.common.schemas import BaseBO


class SmsDispatchBO(BaseBO):
    require_delivery: bool = False
    mobile: str | None
    user_id: int | None
    user_type: int
    template_code: str
    template_params: dict[str, Any]
