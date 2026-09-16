import re

from pydantic import BaseModel

from framework.starter_di.decorators.components import framework
from framework.starter_di.enums.component_scope_enum import ComponentScopeEnum
from framework.starter_job.handler.job_handler import JobHandler
from framework.starter_job.model.job_handler_definition import JobHandlerDefinition


def job(*, key, parameters, source, capability):
    """显式稳定 key 与工作负载能力；不以类名或外部字符串导入处理器。"""
    if not re.fullmatch(r"[a-z][a-z0-9_.:-]{0,127}", key) or not source or not capability:
        raise ValueError("任务 key、来源和能力必须显式声明")
    if not isinstance(parameters, type) or not issubclass(parameters, BaseModel):
        raise TypeError("任务参数必须声明 Pydantic 模型")

    def mark(handler):
        if not issubclass(handler, JobHandler) or "__job__" in vars(handler):
            raise TypeError("任务处理器声明无效或重复")
        handler.__job__ = JobHandlerDefinition(key, parameters, source, capability)
        return framework(scope=ComponentScopeEnum.TRANSIENT)(handler)

    return mark
