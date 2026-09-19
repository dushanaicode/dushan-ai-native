import inspect

from framework.starter_di.definitions.enums.lifecycle_phase_enum import LifecyclePhaseEnum


def post_construct_hook(method):
    """标记单例的同步或异步初始化方法。"""
    if not inspect.isfunction(method):
        raise TypeError("生命周期标记只能用于实例方法")
    method.__di_lifecycle__ = LifecyclePhaseEnum.INITIALIZE
    return method


def pre_destroy_hook(method):
    """标记实例销毁方法，具体资源生命周期由容器管理。"""
    if not inspect.isfunction(method):
        raise TypeError("生命周期标记只能用于实例方法")
    method.__di_lifecycle__ = LifecyclePhaseEnum.DESTROY
    return method
