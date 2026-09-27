from pydantic import BaseModel, ConfigDict


class SocialCallbackRelay(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    redirect_uri: str
    code_parameter: str
