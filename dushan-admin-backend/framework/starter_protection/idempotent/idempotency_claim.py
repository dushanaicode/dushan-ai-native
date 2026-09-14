from dataclasses import dataclass, field

from framework.starter_protection.idempotent.idempotency_rule import IdempotencyRule


@dataclass(frozen=True, slots=True)
class IdempotencyClaim:
    identifier: str = field(repr=False)
    owner: str = field(repr=False)
    rule: IdempotencyRule
