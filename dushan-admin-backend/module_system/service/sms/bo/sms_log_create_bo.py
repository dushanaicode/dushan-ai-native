from typing import Any

from framework.common.schemas import BaseBO
from module_system.dal.dataobject.sms.sms_template_do import SmsTemplateDO


class SmsLogCreateBO(BaseBO):
    mobile: str
    user_id: int | None
    user_type: int
    is_send: bool
    template: SmsTemplateDO
    template_content: str
    template_params: dict[str, Any]
