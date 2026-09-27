from enum import StrEnum


class QrLoginStatus(StrEnum):
    WAITING = "waiting"
    SCANNED = "scanned"
    APPROVED = "approved"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
