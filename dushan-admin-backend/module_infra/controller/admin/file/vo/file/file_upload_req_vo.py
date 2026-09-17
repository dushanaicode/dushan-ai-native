from typing import Annotated, Any

from fastapi import UploadFile
from pydantic import Field, field_validator

from framework.common.schemas.base_request_vo import BaseRequestVO
from framework.common.validator.not_null import NotNull


class FileUploadReqVO(BaseRequestVO):
    """管理后台 - 文件上传 Request VO"""

    file: Annotated[UploadFile, Field(..., description="文件附件")]
    directory: Annotated[str | None, Field(default=None, description="文件目录")]
    model_config = {
        "json_schema_extra": {"examples": [{"file": "文件对象", "directory": "avatar/user"}]}
    }

    @field_validator("file", mode="before")
    @classmethod
    def _validate_file(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="file", value=v, error_msg="文件附件不能为空")
        return v
