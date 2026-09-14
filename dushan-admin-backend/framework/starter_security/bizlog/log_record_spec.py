from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LogRecordSpec:
    """受限 Jinja 模板；capture 显式选择参数，结果只从调用作用域提供。"""

    type: str
    sub_type: str
    success: str
    biz_no: str
    fail: str = "操作失败"
    extra: str | None = None
    condition: str | None = None
    success_condition: str | None = None
    capture: tuple[str, ...] = ()

    def __post_init__(self):
        if any(not value or len(value) > 50 for value in (self.type, self.sub_type)):
            raise ValueError("业务日志分类必须为 1 到 50 个字符")
        if not self.success or not self.fail or not self.biz_no:
            raise ValueError("业务日志需要成功、失败及业务编号模板")
        if len(set(self.capture)) != len(self.capture) or "self" in self.capture:
            raise ValueError("日志参数不能重复或包含整个服务实例")
