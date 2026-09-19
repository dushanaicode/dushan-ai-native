from datetime import datetime

from framework.common.schemas import BaseDTO


class TenantPackageCacheDTO(BaseDTO):
    id: int
    creator: str
    updater: str
    create_time: datetime
    update_time: datetime
    deleted: bool
    name: str
    status: int
    remark: str | None
    menu_ids: list[int]
    quota_config: dict | None
