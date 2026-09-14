from pydantic import BaseModel, ConfigDict, Field


class AuthorizationRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    url: str | None = Field(repr=False)
    state: str = Field(repr=False)
    expires_in: int
