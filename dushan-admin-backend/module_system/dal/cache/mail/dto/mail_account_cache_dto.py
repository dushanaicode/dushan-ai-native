from datetime import datetime

from framework.common.schemas.base_dto import BaseDTO


class MailAccountCacheDTO(BaseDTO):
    id: int
    creator: str
    updater: str
    create_time: datetime
    update_time: datetime
    deleted: bool
    mail: str
    username: str
    password: str
    host: str
    port: int
    ssl_enable: bool
    starttls_enable: bool
