from dataclasses import dataclass

from pydantic import BaseModel


@dataclass(frozen=True, slots=True)
class JobHandlerDefinition:
    key: str
    parameters: type[BaseModel]
    source: str
    capability: str
