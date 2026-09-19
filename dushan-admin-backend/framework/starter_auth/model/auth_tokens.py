import json
from typing import ClassVar, Self

from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError, field_validator

from framework.starter_auth.definitions.constants.auth_error_codes import AuthErrorCodes as Codes
from framework.starter_auth.exception.auth_exception import AuthException


class AuthTokens(BaseModel):
    """只供服务端使用的第三方凭据，绑定稳定的应用、授权源和 client_id。

    普通 repr/JSON 用于安全展示。可信服务端存储使用 to_storage_json，得到的
    SecretStr 只有显式 get_secret_value 后才可写入业务存储；读取后使用
    from_storage_json。存储加密、访问控制和刷新结果的原子替换由业务负责，
    不能把浏览器提供的 JSON 当作可信凭据恢复。
    """

    model_config = ConfigDict(frozen=True, extra="forbid")
    application_id: str
    source: str
    client_id: str = Field(min_length=1, max_length=256)
    access_token: SecretStr | None = Field(default=None, min_length=1, repr=False, exclude=True)
    refresh_token: SecretStr | None = Field(default=None, min_length=1, repr=False, exclude=True)
    id_token: SecretStr | None = Field(default=None, min_length=1, repr=False, exclude=True)
    session_key: SecretStr | None = Field(default=None, min_length=1, repr=False, exclude=True)
    expires_in: int | None = Field(default=None, ge=0)
    refresh_expires_in: int | None = Field(default=None, ge=0)
    token_type: str | None = None
    scope: str | None = None
    subject: str | None = Field(default=None, min_length=1)
    subject_type: str | None = Field(default=None, min_length=1)
    union_id: str | None = None
    nonce: str | None = Field(default=None, min_length=1, repr=False, exclude=True)
    claims: dict | None = Field(default=None, repr=False, exclude=True)
    data: dict[str, object] = Field(default_factory=dict, repr=False, exclude=True)

    _SECRET_FIELDS: ClassVar[tuple[str, ...]] = (
        "access_token",
        "refresh_token",
        "id_token",
        "session_key",
    )
    _PRIVATE_DATA_KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "access_token",
            "refresh_token",
            "id_token",
            "session_key",
            "client_secret",
            "accesstoken",
            "refreshtoken",
            "idtoken",
            "sessionkey",
            "clientsecret",
            "code",
            "auth_code",
            "code_verifier",
            "mac_key",
            "oauth_token_secret",
            "user_ticket",
        }
    )

    @field_validator("data")
    @classmethod
    def remove_credential_copies(cls, data: dict) -> dict:
        """协议原文只保留资料及非敏感元数据，不持有凭据的明文副本。"""
        return cls._public_data(data)

    @classmethod
    def _public_data(cls, value):
        if isinstance(value, dict):
            return {
                key: cls._public_data(item)
                for key, item in value.items()
                if key.lower() not in cls._PRIVATE_DATA_KEYS
            }
        if isinstance(value, list):
            return [cls._public_data(item) for item in value]
        return value

    def to_storage_json(self) -> SecretStr:
        """显式导出包含秘密和 OIDC 上下文的记录，默认字符串表现仍保持遮蔽。"""
        record = self.model_dump(mode="json")
        for name in self._SECRET_FIELDS:
            secret = getattr(self, name)
            record[name] = None if secret is None else secret.get_secret_value()
        record.update(nonce=self.nonce, claims=self.claims, data=self.data)
        return SecretStr(
            json.dumps(record, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        )

    @classmethod
    def from_storage_json(cls, value: str) -> Self:
        """恢复可信存储记录；格式错误通过安全异常传播，不回显原文。"""
        try:
            return cls.model_validate_json(value)
        except ValidationError as error:
            raise AuthException(Codes.INPUT, cause=error) from error
