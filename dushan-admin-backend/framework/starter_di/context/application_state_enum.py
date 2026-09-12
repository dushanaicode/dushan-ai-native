from framework.common.enums.base_enum import BaseEnum


class ApplicationStateEnum(BaseEnum):
    """容器初始化和应用开放业务、排空业务分别记录。"""

    NEW = ("new", "未启动")
    STARTING = ("starting", "资源装配中")
    READY = ("ready", "接收业务")
    DRAINING = ("draining", "等待业务结束")
    STOPPING = ("stopping", "释放资源")
    CLOSED = ("closed", "已关闭")
