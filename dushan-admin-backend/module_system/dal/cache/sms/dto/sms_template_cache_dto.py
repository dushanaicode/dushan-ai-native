from datetime import datetime

from framework.common.schemas import BaseDTO


class SmsTemplateCacheDTO(BaseDTO):
    id: int
    creator: str
    updater: str
    create_time: datetime
    update_time: datetime
    deleted: bool
    type: int
    builtin: int
    status: int
    code: str
    name: str
    content: str
    params: list[str]
    remark: str | None
    api_template_id: str
    channel_id: int
    channel_code: str
