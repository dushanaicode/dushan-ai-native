from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from framework.common.exception.core.field_error import FieldError


class ErrorDetails(BaseModel):
    """承载可公开的字段、重试和受控调试详情，不参与错误码分类。

    无明细时响应error为null；fields供当前表单映射，其他字段由实际能力填入。
    debug只由启用调试的响应构造器生成，不能直接传入原始异常对象。
    """

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    fields: tuple[FieldError, ...] = ()
    retryable: bool | None = None
    retry_after: int | None = Field(default=None, alias="retryAfter", ge=0)
    debug: dict[str, Any] | None = None
