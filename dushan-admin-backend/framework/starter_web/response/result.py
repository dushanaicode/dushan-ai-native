from typing import Generic, TypeVar

from pydantic import StrictInt

from framework.common.exception.constants.global_error_code_constants import (
    GlobalErrorCodeConstants,
)
from framework.common.exception.core.error_details import ErrorDetails
from framework.common.schemas.base_vo import BaseVO

T = TypeVar("T")


class Result(BaseVO, Generic[T]):
    """定义code/message/data/error统一业务响应。

    Result.success(data)构造成功码0，普通业务JSON使用HTTP 200。
    data 应是公开数据或明确的响应模型，模型序列化不能代替字段授权。
    """

    code: StrictInt
    data: T | None = None
    message: str = "ok"
    error: ErrorDetails | None = None

    @classmethod
    def success(cls, data: T | None = None, message: str = "ok") -> "Result[T]":
        """构造成功响应，不接受覆盖成功码或未知扩展参数。"""
        return cls(code=GlobalErrorCodeConstants.SUCCESS.code, data=data, message=message)
