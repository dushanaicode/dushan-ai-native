from framework.common.schemas.base_bo import BaseBO


class NoticeLogResultBO(BaseBO):
    notice_log_id: int
    success_count: int
    fail_count: int
