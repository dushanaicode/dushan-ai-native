from framework.starter_database.model.base_do import BaseDO


class GlobalControlDO(BaseDO):
    """全局控制数据基类；具体模型显式使用 global_model 声明。"""

    __abstract__ = True
