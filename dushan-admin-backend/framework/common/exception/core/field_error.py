from pydantic import BaseModel, ConfigDict, Field


class FieldError(BaseModel):
    """描述本次请求中一个可公开的字段错误。

    field使用表单字段路径，例如contacts[0].mobile；空字符串表示表单整体错误。
    message是可展示提示，不包含原始输入、内部异常或数据库信息。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    field: str
    message: str = Field(min_length=1)
