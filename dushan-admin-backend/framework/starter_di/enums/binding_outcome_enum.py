from framework.common.enums.base_enum import BaseEnum


class BindingOutcomeEnum(BaseEnum):
    """启动装配时每个 DI 候选的选择结果，只描述本次配置快照下的决定。"""

    SELECTED = ("selected", "已选中")
    MISSING_MODULE = ("missing_module", "依赖模块未启用")
    CONDITION_FALSE = ("condition_false", "条件不满足")
    DEFAULT_REPLACED = ("default_replaced", "默认实现被条件实现替代")
    CONFLICT = ("conflict", "同一绑定键存在多个候选")
