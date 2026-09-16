from framework.common.exception.constants.global_error_code_constants import (
    GlobalErrorCodeConstants,
)
from framework.common.exception.exceptions.base_business_exception import BaseBusinessException


class JobException(BaseBusinessException):
    def __init__(self, reason, *, cause=None):
        messages = {
            "configuration": "任务调度配置或 SPI 未就绪",
            "handler": "任务处理器不存在或重复",
            "parameters": "任务参数无效",
            "cron": "Cron 必须为有效标准五段表达式",
            "disabled": "任务不存在或已停用",
            "capacity": "任务执行请求队列已满",
            "owner": "当前进程未持有调度租约",
            "closed": "任务运行时已关闭",
            "snapshot": "任务定义已变化，旧请求跳过",
        }
        super().__init__(
            GlobalErrorCodeConstants.SERVICE_UNAVAILABLE
            if reason in {"configuration", "closed", "owner"}
            else GlobalErrorCodeConstants.BAD_REQUEST,
            msg=messages[reason],
            cause=cause,
        )
        self.reason = reason

    def __safe_diagnostic__(self):
        return JobException(self.reason)
