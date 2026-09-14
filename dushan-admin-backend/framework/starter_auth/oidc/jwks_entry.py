import asyncio
from dataclasses import dataclass, field


@dataclass(slots=True)
class JwksEntry:
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    keys: object = None
    expires_at: float = 0
    retry_after: float = 0
    refresh_after: float = 0
    discovery_expires_at: float = 0
    generation: int = 0
