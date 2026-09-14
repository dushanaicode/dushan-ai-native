from dataclasses import dataclass
from typing import ClassVar

from framework.starter_web.routing.operate_type_enum import OperateTypeEnum


@dataclass(frozen=True, slots=True)
class AccessLogPolicy:
    """声明端点是否记录访问元数据，不读取正文，也不改变函数签名。"""

    ATTRIBUTE: ClassVar[str] = "__web_access_log__"
    enabled: bool
    operate_module: str = ""
    operate_name: str = ""
    operate_type: OperateTypeEnum | None = None

    def __call__(self, endpoint):
        previous = getattr(endpoint, self.ATTRIBUTE, None)
        if previous is not None and previous != self:
            raise ValueError("端点访问日志声明冲突")
        setattr(endpoint, self.ATTRIBUTE, self)
        return endpoint
