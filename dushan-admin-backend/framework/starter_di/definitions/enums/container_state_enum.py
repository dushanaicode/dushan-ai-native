from framework.common.enums.base_enum import BaseEnum


class ContainerStateEnum(BaseEnum):
    """容器只经历一次创建、启动、运行和关闭。"""

    NEW = ("new", "未启动")
    STARTING = ("starting", "启动中")
    READY = ("ready", "已就绪")
    STOPPING = ("stopping", "关闭中")
    CLOSED = ("closed", "已关闭")
