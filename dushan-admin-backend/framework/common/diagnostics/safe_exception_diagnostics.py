class SafeExceptionDiagnostics:
    """按异常提供的安全投影隔离敏感原因、堆栈局部变量及异常组。

    敏感异常实现 __safe_diagnostic__ 返回无原始引用的异常副本；普通异常保持
    原有诊断行为。含敏感后代的包装节点只保留类型和结构，不复制其文本或堆栈。
    """

    @classmethod
    def snapshot(cls, error: BaseException) -> BaseException:
        if not cls._contains_sensitive(error, set()):
            return error
        return cls._snapshot(error, set())

    @classmethod
    def _contains_sensitive(cls, error, visited):
        if id(error) in visited:
            return False
        visited.add(id(error))
        if callable(getattr(error, "__safe_diagnostic__", None)):
            return True
        children = list(error.exceptions) if isinstance(error, BaseExceptionGroup) else []
        children.extend(item for item in (error.__cause__, error.__context__) if item is not None)
        return any(cls._contains_sensitive(item, visited) for item in children)

    @classmethod
    def _snapshot(cls, error, visited):
        if id(error) in visited:
            return Exception("重复异常引用")
        visited.add(id(error))
        project = getattr(error, "__safe_diagnostic__", None)
        if callable(project):
            safe = project()
            # 清理错误组属于独立失败，不是敏感驱动原始 cause，保留其安全结构。
            if isinstance(error.__cause__, BaseExceptionGroup):
                safe.__cause__ = cls._snapshot(error.__cause__, visited)
            return safe
        if isinstance(error, BaseExceptionGroup):
            safe = BaseExceptionGroup(
                "安全诊断异常组", [cls._snapshot(item, visited) for item in error.exceptions]
            )
        else:
            safe = Exception(type(error).__name__)
        cause = error.__cause__
        if cause is None and not error.__suppress_context__:
            cause = error.__context__
        if cause is not None:
            safe.__cause__ = cls._snapshot(cause, visited)
        safe.__suppress_context__ = True
        return safe
