from typing import Any

from framework.common.schemas import BaseBO


class NoticeLogCreateBO(BaseBO):
    notice_id: int
    notice_title: str
    notice_type: int
    push_target_type: int
    target_user_ids: list[int] | None
    target_dept_ids: list[int] | None
    target_dept_names: list[str] | None
    push_channels: list[str]
    total_count: int
    publisher_info: dict[str, Any] | None
