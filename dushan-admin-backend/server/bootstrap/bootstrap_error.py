class BootstrapError(RuntimeError):
    """启动步骤执行失败，报错时保留步骤名称和原始异常。"""
