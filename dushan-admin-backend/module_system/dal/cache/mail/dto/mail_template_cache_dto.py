from datetime import datetime

from framework.common.schemas.base_dto import BaseDTO


class MailTemplateCacheDTO(BaseDTO):
    id: int
    creator: str
    updater: str
    create_time: datetime
    update_time: datetime
    deleted: bool
    name: str
    code: str
    account_id: int
    nickname: str | None
    title: str
    content: str
    params: list[str]
    status: int
    remark: str | None
