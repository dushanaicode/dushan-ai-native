from typing import Any

from framework.common.schemas.base_bo import BaseBO


class SmsDispatchBO(BaseBO):
    mobile: str | None
    user_id: int | None
    user_type: int
    template_code: str
    template_params: dict[str, Any]
