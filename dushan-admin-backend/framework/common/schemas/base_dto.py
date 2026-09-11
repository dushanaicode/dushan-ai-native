from pydantic import BaseModel, ConfigDict


class BaseDTO(BaseModel):
    """定义跨模块 API/SPI 数据契约，保持 Python 字段名和字符串原值。

    子类声明允许传输的字段，未知字段拒绝，赋值和默认值同样接受校验。
    例如 UserDTO.model_validate(user) 从对象属性读取已声明字段，
    dto.model_dump() 输出 Python 数据，dto.model_dump(mode="json") 输出可编码数据。
    字段须使用 Pydantic 支持的类型；数据库操作与输出脱敏由调用方负责。
    """

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
        validate_assignment=True,
        validate_default=True,
    )
