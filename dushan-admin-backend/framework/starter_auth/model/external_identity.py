from pydantic import BaseModel, ConfigDict, Field


class ExternalIdentity(BaseModel):
    """原始 subject 按应用、来源、客户端和 subject_type 区分；不自动合并账号。"""

    model_config = ConfigDict(frozen=True, extra="forbid")
    application_id: str
    source: str
    client_id: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    subject_type: str = Field(min_length=1)
    issuer: str | None = None
    union_id: str | None = None
    username: str | None = None
    nickname: str | None = None
    avatar: str | None = None
    email: str | None = None
    email_verified: bool | None = None
    gender: str | None = None
    location: str | None = None
    blog: str | None = None
    company: str | None = None
    remark: str | None = None
    snapshot_user: bool = False
    raw: dict = Field(default_factory=dict, repr=False, exclude=True)
