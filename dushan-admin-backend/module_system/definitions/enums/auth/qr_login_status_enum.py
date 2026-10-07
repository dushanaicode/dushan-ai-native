from framework.common.enums import BaseEnum


class QrLoginStatusEnum(BaseEnum):
    WAITING = ("waiting", "等待扫码")
    SCANNED = ("scanned", "已扫码")
    APPROVED = ("approved", "已确认")
    CANCELLED = ("cancelled", "已取消")
    EXPIRED = ("expired", "已过期")
