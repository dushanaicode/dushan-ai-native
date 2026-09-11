from pydantic import BaseModel, ConfigDict


class BaseBO(BaseModel):
    """定义服务内部的业务对象、命令和消息。

    子类声明业务字段，使用具体子类的 model_validate(data) 构造并校验对象。
    保持 Python 字段名和字符串原值，拒绝未知字段，校验赋值和默认值。
    可声明运行时类型；持有资源对象不代表本模型负责创建或关闭资源。
    运行时对象不保证可序列化为 JSON；对外传输应转换为明确的 DTO/VO。
    """

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        from_attributes=True,
        extra="forbid",
        validate_assignment=True,
        validate_default=True,
    )
