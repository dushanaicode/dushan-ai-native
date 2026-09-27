from framework.common.schemas import BaseVO


class CacheCleanupPresetRespVO(BaseVO):
    code: str
    title: str
    description: str
    high_risk: bool
    available: bool
    patterns: list[str]
