from fastapi import Path
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from framework.common.contracts.snowflake_id import SnowflakeIdInput
from framework.common.schemas.base_request_vo import BaseRequestVO


class OnlineDeviceReqVO(BaseRequestVO):
    token_id: SnowflakeIdInput

    @classmethod
    async def from_path(cls, token_id: str = Path(alias="tokenId")) -> "OnlineDeviceReqVO":
        """保留路径原始字符串，由 VO 一次性校验雪花编号。"""
        try:
            return cls(token_id=token_id)
        except ValidationError as error:
            raise RequestValidationError(
                [
                    {**item, "loc": ("path", *item["loc"])}
                    for item in error.errors(include_url=False, include_input=False)
                ]
            ) from error
