from dataclasses import dataclass


@dataclass(slots=True)
class ConfigNotification:
    """通知区间结束时撤销标记，后续任务不再被误判为当前回调重入。"""

    active: bool = True
