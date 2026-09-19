from datetime import datetime

from framework.common.schemas import BaseDTO


class RoleCacheDTO(BaseDTO):
    id: int
    creator: str
    updater: str
    create_time: datetime
    update_time: datetime
    deleted: bool
    tenant_id: str
    name: str
    code: str
    sort: int
    data_scope: int
    data_scope_dept_ids: list[int]
    builtin: int
    status: int
    remark: str | None
    active_key: int | None
