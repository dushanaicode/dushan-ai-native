from typing import Any

from framework.common.schemas import BaseBO
from module_system.dal.dataobject.mail.mail_account_do import MailAccountDO
from module_system.dal.dataobject.mail.mail_template_do import MailTemplateDO


class MailBatchLogCreateBO(BaseBO):
    user_id: int
    user_type: int
    to_mails: list[str]
    cc_mails: list[str] | None
    bcc_mails: list[str] | None
    account: MailAccountDO
    template: MailTemplateDO
    template_content: str
    template_params: dict[str, Any]
    is_send: bool
