from dataclasses import dataclass


@dataclass(eq=False, slots=True)
class DatabaseOperation:
    """完整数据库操作的准入租约，覆盖提交后的必要动作与预登记后台任务。"""

    active: bool = True
