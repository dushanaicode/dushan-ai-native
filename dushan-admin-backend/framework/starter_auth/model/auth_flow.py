from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class AuthFlow:
    state: str = field(repr=False)
    verifier: str = field(default="", repr=False)
    nonce: str = field(default="", repr=False)
