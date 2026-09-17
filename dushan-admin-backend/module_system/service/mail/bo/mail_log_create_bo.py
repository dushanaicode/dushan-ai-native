from typing import Any

from framework.common.schemas.base_bo import BaseBO
from module_system.dal.dataobject.mail.mail_account_do import MailAccountDO
from module_system.dal.dataobject.mail.mail_template_do import MailTemplateDO


class MailLogCreateBO(BaseBO):
    user_id: int
    user_type: int
    to_mail: str
    account: MailAccountDO
    template: MailTemplateDO
    template_content: str
    template_params: dict[str, Any]
    is_send: bool
